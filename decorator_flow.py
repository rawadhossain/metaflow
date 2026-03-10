from metaflow import FlowSpec, step, environment

class DecoratorFlow(FlowSpec):

    @environment(vars={"HELLO": "WORLD"})
    @step
    def start(self):
        import os
        print(os.environ["HELLO"])
        self.next(self.end)

    @step
    def end(self):
        pass

if __name__ == "__main__":
    DecoratorFlow()