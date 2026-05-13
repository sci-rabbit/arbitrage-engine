class Stage:
    name: str

    def process_batch(self, items):
        """
        Возвращает:
        passed_items, invalid_pairs
        """
        raise NotImplementedError
