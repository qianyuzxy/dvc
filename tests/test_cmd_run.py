import os
import shutil
import subprocess
import tempfile
from unittest import TestCase

from dvc.command.run import CmdRun, RunError
from dvc.config import ConfigI
from dvc.path.data_item import DataItem
from dvc.path.factory import PathFactory
from dvc.git_wrapper import GitWrapperI
from dvc.repository_change import RepositoryChange


class RunBasicTest(TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self._old_curr_dir_abs = os.path.realpath(os.curdir)

        self.tearDown()
        os.mkdir(self.test_dir)
        os.chdir(self.test_dir)
        os.mkdir('data')
        os.mkdir('cache')
        os.mkdir('state')

        self._devnull = open(os.devnull, 'w')
        subprocess.Popen(['git', 'init'], stdout=self._devnull, stderr=None).wait()

        self.commit = 'abc1234'
        self.git = GitWrapperI(self.test_dir, self.commit)
        self.config = ConfigI('data', 'cache', 'state')
        self.path_factory = PathFactory(self.git, self.config)
        pass

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)
        os.chdir(self._old_curr_dir_abs)

    @staticmethod
    def create_file(file2):
        fd = open(file2, 'w+')
        fd.write('random text')
        fd.close()


class TestRunOutsideData(RunBasicTest):
    def test(self):
        cmd_run = CmdRun(config_obj=self.config)
        with self.assertRaises(RunError):
            state = cmd_run.run_command(['touch', 'file1', 'file2'], [])
            next(state)
        pass


class RunTwoFilesBase(RunBasicTest):
    def setUp(self):
        super(RunTwoFilesBase, self).setUp()

        cmd_run = CmdRun(config_obj=self.config, git_obj=self.git)
        self.input_param_file = 'data/extra_input'
        cmd_run.args.input = [self.input_param_file]

        self.extra_output_file = 'data/extra_output'
        cmd_run.args.output = [self.extra_output_file]

        self.file_name1 = 'data/file1'
        self.file_name2 = 'data/file2'
        self.state_objs = cmd_run.run_command(['touch', self.file_name1, self.file_name2], [])

        self.state_file_name1 = 'state/file1' + DataItem.STATE_FILE_SUFFIX
        self.state_file_name2 = 'state/file2' + DataItem.STATE_FILE_SUFFIX

        self.state_file1 = None
        self.state_file2 = None
        for s in self.state_objs:
            if s.file == self.state_file_name1:
                self.state_file1 = s
            elif s.file == self.state_file_name2:
                self.state_file2 = s
        pass


class TestRunStateFiles(RunTwoFilesBase):
    def test(self):
        names = [x.file for x in self.state_objs]
        self.assertEqual({self.state_file_name1, self.state_file_name2}, set(names))


class TestRunExtraInExtraOutFiles(RunTwoFilesBase):
    def test(self):
        self.assertIsNotNone(self.state_file1)
        self.assertEqual(self.state_file1.input_files, [self.input_param_file])

        output_set = {self.file_name1, self.file_name2, self.extra_output_file}
        self.assertEqual(set(self.state_file1.output_files), output_set)
