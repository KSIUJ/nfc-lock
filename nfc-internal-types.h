// Extracted from libnfc nfc-internal.h in order to access internal api.
// Must be kept in sync with current libnfc version.

#ifndef __NFC_INTERNAL_TYPES_H__
#define __NFC_INTERNAL_TYPES_H__

#include <stdbool.h>

#define DEVICE_NAME_LENGTH  256

struct nfc_driver;
struct nfc_context;

/**
 * @struct nfc_device
 * @brief NFC device information
 */
struct nfc_device {
  const nfc_context *context;
  const struct nfc_driver *driver;
  void *driver_data;
  void *chip_data;

  /** Device name string, including device wrapper firmware */
  char    name[DEVICE_NAME_LENGTH];
  /** Device connection string */
  nfc_connstring connstring;
  /** Is the CRC automaticly added, checked and removed from the frames */
  bool    bCrc;
  /** Does the chip handle parity bits, all parities are handled as data */
  bool    bPar;
  /** Should the chip handle frames encapsulation and chaining */
  bool    bEasyFraming;
  /** Should the chip try forever on select? */
  bool    bInfiniteSelect;
  /** Should the chip switch automatically activate ISO14443-4 when
      selecting tags supporting it? */
  bool    bAutoIso14443_4;
  /** Supported modulation encoded in a byte */
  uint8_t  btSupportByte;
  /** Last reported error */
  int     last_error;
};

#endif // __NFC_INTERNAL_TYPES_H__