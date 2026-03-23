from metaflow import FlowSpec, step, environment

class OrderingTestFlow(FlowSpec):

    @environment(vars={"A": "1"})
    @step
    def start(self):
        print("running start")
        self.next(self.end)

    @step
    def end(self):
        print("running end")

if __name__ == "__main__":
    OrderingTestFlow()