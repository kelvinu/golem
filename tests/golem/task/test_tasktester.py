from mock import Mock

from golem.task.taskbase import Task
from golem.task.tasktester import TaskTester, logger
from golem.tools.testdirfixture import TestDirFixture
from golem.tools.assertlogs import LogTestCase


class TaskThread:
    def __init__(self, result):
        self.result = result
        self.error = False


class MemTaskThread(TaskThread):
    def __init__(self, result, memory, error):
        TaskThread.__init__(self, (result, memory))
        self.error_msg = error
        self.error = False

    def get_error(self):
        return self.error

    def get_progress(self):
        return "30%"


class TestTaskTester(TestDirFixture, LogTestCase):
    task = Task(Mock(), Mock())
    node = 'node1'
    task_name = 'task1'

    def test_init(self):
        self.task.query_extra_data_for_test_task = Mock()
        self.assertIsNotNone(TaskTester(self.task, self.path, None, None))

    def test_task_computed(self):
        result = [{"data": True}, 123]

        self.task.header.node_name = self.node
        self.task.header.task_id = self.task_name
        self.task.root_path = self.path
        self.task.after_test = lambda res, tmp_dir: {}
        self.task.query_extra_data_for_test_task = Mock()

        tt = TaskTester(self.task, self.path, Mock(), Mock())
        tt.tmp_dir = self.path
        task_thread = TaskThread(result)
        tt.task_computed(task_thread)

        task_thread = MemTaskThread(None, 30210, "Some error")
        with self.assertLogs(logger, level='WARNING'):
            tt.task_computed(task_thread)
        tt.error_callback.assert_called_with("Some error")

        task_thread = MemTaskThread("result", 2010, "Another error")
        self.assertIsNone(tt.get_progress())
        tt.tt = task_thread
        self.assertEqual(tt.get_progress(), "30%")
        task_thread.error = True
        self.assertEqual(tt.get_progress(), 0)
        tt.task_computed(task_thread)
        tt.error_callback.assert_called_with("Another error")

        self.message = ""

        def success_callback(res, est_mem, time_spent, after_test_data):
            self.message = "Success " + after_test_data["warnings"]

        self.task.header.node_name = self.node
        self.task.header.task_id = self.task_name
        self.task.root_path = self.path
        self.task.after_test = lambda res, tmp_dir: {"warnings": "bla ble"}
        self.task.query_extra_data_for_test_task = Mock()

        tt = TaskTester(self.task, self.path, success_callback, None)
        tt.tmp_dir = self.path
        task_thread = TaskThread(result)
        tt.task_computed(task_thread)
        self.assertTrue("bla" in self.message)
        self.assertTrue("ble" in self.message)

    def test_is_success(self):
        self.task.query_extra_data_for_test_task = Mock()
        tt = TaskTester(self.task, self.path, Mock(), Mock())
        task_thread = Mock()

        # Proper task
        task_thread.error = None
        task_thread.result = ({"data": True}, 123)
        assert tt.is_success(task_thread)

        # Task thead result first arg is not tuple
        task_thread.result = {"data": True}
        assert not tt.is_success(task_thread)
        assert task_thread.error == "Wrong result format"