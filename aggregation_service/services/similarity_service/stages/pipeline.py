from services.similarity_service.stages.dataclass import PairItem


class SimilarityPipeline:
    def __init__(self, stages, batch_size=200):
        self.stages = stages
        self.batch_size = batch_size

    def run(self, items: list[PairItem]):
        for i in range(0, len(items), self.batch_size):
            batch = items[i : i + self.batch_size]

            current = batch

            for stage in self.stages:
                if not current:
                    break

                current, invalid = stage.process_batch(current)

                if invalid:
                    yield {
                        "stage": stage.name,
                        "invalid_pairs": invalid,
                    }

            if current:
                yield {
                    "stage": "result",
                    "valid_pairs": current,
                }
