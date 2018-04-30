#include <err.h>
#include <inttypes.h>
#include <signal.h>
#include <stdio.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <nfc/nfc.h>
#include <nfc/nfc-types.h>

// We provide this file to access internal libnfc features
#include "nfc-internal-types.h"

static nfc_device *pnd = NULL;
static nfc_context *context;

static void stop_polling(int sig) {
    (void) sig;
    if (pnd != NULL)
        nfc_abort_command(pnd);
    else {
        nfc_exit(context);
        exit(EXIT_FAILURE);
    }
}

int main(int argc, const char *argv[]) {
    signal(SIGINT, stop_polling);

    const uint8_t uiPollNr = 50;
    const uint8_t uiPeriod = 1;
    const nfc_modulation nmModulations[1] = {
            {.nmt = NMT_ISO14443A, .nbr = NBR_106},
    };
    const size_t szModulations = 1;

    nfc_target nt;
    int res = 0;

    nfc_init(&context);
    if (context == NULL) {
        fprintf(stderr, "Unable to init libnfc (malloc)");
        exit(EXIT_FAILURE);
    }

    pnd = nfc_open(context, NULL);

    if (pnd == NULL) {
        fprintf(stderr, "Unable to open NFC device.");
        nfc_exit(context);
        exit(EXIT_FAILURE);
    }

    if (nfc_initiator_init(pnd) < 0) {
        nfc_perror(pnd, "nfc_initiator_init");
        nfc_close(pnd);
        nfc_exit(context);
        exit(EXIT_FAILURE);
    }

    while (1) {
        do {
            res = nfc_initiator_poll_target(pnd, nmModulations, szModulations, uiPollNr, uiPeriod, &nt);
        } while (res <= 0 && pnd->last_error == NFC_SUCCESS);

        if (res < 0) {
            nfc_perror(pnd, "nfc_initiator_poll_target");
            nfc_close(pnd);
            nfc_exit(context);
            exit(EXIT_FAILURE);
        }

        if (res > 0) {
            if (nt.nm.nmt != NMT_ISO14443A) {
                fprintf(stderr, "Unsupported card type\n");
                exit(EXIT_FAILURE);
            }
            for (int i = 0; i < nt.nti.nai.szUidLen; i++) {
                printf("%02x", nt.nti.nai.abtUid[i]);
            }
            printf("\n");
            fflush(stdout);
        }
        while (0 == nfc_initiator_target_is_present(pnd, NULL)) {}
        sleep(1);
    }

    nfc_close(pnd);
    nfc_exit(context);
    exit(EXIT_SUCCESS);
}