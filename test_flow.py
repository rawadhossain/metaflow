from metaflow import FlowSpec, step

class TestFlow(FlowSpec):

    @step
    def start(self):
        print("start")
        self.next(self.end)

    @step
    def end(self):
        print("end")

if __name__ == "__main__":
    TestFlow()