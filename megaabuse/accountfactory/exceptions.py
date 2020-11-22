class WaitForMailTimoutException(Exception):
    def __init__(self, timout):
        self.timout = timout
        self.message = f"Timout exceeded {timout} seconds"
        super().__init__(self.message)

    def __str__(self):
        return f'{self.timout} -> {self.message}'
