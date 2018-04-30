import subprocess
import signal


class NFCReader:
    singleton = None

    class _NFCReader:
        def __init__(self):
            self.process = subprocess.Popen("./reader", stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        def get_card_uid(self):
            line = self.process.stdout.readline()
            if line == b"":
                self.process.terminate()
                self.process = subprocess.Popen("./reader", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                raise Exception(self.process.stderr.readline().decode())
            return line.decode().strip()

        def close(self):
            self.process.send_signal(signal.SIGINT)

    def __enter__(self):
        if NFCReader.singleton is not None:
            raise Exception("Only one NFCReader instance allowed")

        NFCReader.singleton = self._NFCReader()
        return NFCReader.singleton

    def __exit__(self, exc_type, exc_val, exc_tb):
        NFCReader.singleton = None
