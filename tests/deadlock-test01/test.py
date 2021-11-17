import lldb
import os
import deadlock_detector
import test_tools
import time
import threading


class TestSimpleDeadlockClang(test_tools.MySetUpTestCase):
    def setUp(self) -> None:
        self.mySetUp([], "clang++")

    def test_run(self) -> None:
        # process: lldb.SBProcess
        # process = lldb.SBProcess()
        #
        # def run_exe(process1: lldb.SBProcess):
        #     process1 = self.target.LaunchSimple(None, None, os.getcwd())
        #
        # t1 = threading.Thread(target=run_exe, args=(process))
        # print("here 1")
        # t1.start()
        # time.sleep(3)
        # process.Stop()
        # print("here 2")
        # self.assertFalse(deadlock_detector.find_deadlock(self.debugger)[0])
        # lldb.SBDebugger.Destroy(self.debugger)
        def print1(x):
            for i in range(1000):
                print(x)

        def print2():
            for i in range(1000):
                print(x + 1)

        t1 = threading.Thread(target=print1, args=(1,))
        t2 = threading.Thread(target=print2, args=(2,))
        t1.start()
        t2.start()
        t1.join()
        t2.join()



