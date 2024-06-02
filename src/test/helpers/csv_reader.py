
class CsvReader:
    __LINES: list[list[str]]

    def __init__(self, csv_path: str):
        self.__csv_path = csv_path

    def read_data_csv(self) -> None:
        with open(self.__csv_path) as file:
            self.__LINES = [line.split(',') for line in file.readlines()[1:]]
        return self.__LINES
