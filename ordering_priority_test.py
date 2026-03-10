from metaflow import FlowSpec, step
from metaflow.decorators import StepDecorator


def step_deco(deco_cls):
    def decorator(func):
        if not hasattr(func, "is_step"):
            from metaflow.decorators import BadStepDecoratorException
            raise BadStepDecoratorException(deco_cls.name, func)
            
        if deco_cls.name in [deco.name for deco in func.decorators]:
            from metaflow.decorators import DuplicateStepDecoratorException
            raise DuplicateStepDecoratorException(deco_cls.name, func)
        func.decorators.append(deco_cls(attributes={}, statically_defined=True))
        return func
    return decorator


class FirstDecorator(StepDecorator):
    name = "first"
    ORDER_PRIORITY = 10

    def task_pre_step(
        self, step_name, task_datastore, metadata, run_id, task_id, flow, graph, retry_count, max_user_code_retries, ubf_context, inputs
    ):
        print("FIRST decorator executed")


class SecondDecorator(StepDecorator):
    name = "second"
    ORDER_PRIORITY = 10

    def task_pre_step(
        self, step_name, task_datastore, metadata, run_id, task_id, flow, graph, retry_count, max_user_code_retries, ubf_context, inputs
    ):
        print("SECOND decorator executed")


class ThirdDecorator(StepDecorator):
    name = "third"
    ORDER_PRIORITY = 10

    def task_pre_step(
        self, step_name, task_datastore, metadata, run_id, task_id, flow, graph, retry_count, max_user_code_retries, ubf_context, inputs
    ):
        print("THIRD decorator executed")


class OrderingPriorityTestFlow(FlowSpec):

    @step_deco(FirstDecorator)
    @step_deco(SecondDecorator)
    @step_deco(ThirdDecorator)
    @step
    def start(self):
        print("STEP BODY")
        self.next(self.end)

    @step
    def end(self):
        print("END STEP")


if __name__ == "__main__":
    OrderingPriorityTestFlow()