
from mock import patch
from mock import call
import mock
import sys

from .test_helper import *

from kiwi.exceptions import *
from kiwi.storage.subformat.vhdfixed import DiskFormatVhdFixed


class TestDiskFormatVhdFixed(object):
    @patch('platform.machine')
    def setup(self, mock_machine):
        mock_machine.return_value = 'x86_64'
        xml_data = mock.Mock()
        xml_data.get_name = mock.Mock(
            return_value='some-disk-image'
        )
        self.xml_state = mock.Mock()
        self.xml_state.xml_data = xml_data
        self.xml_state.get_image_version = mock.Mock(
            return_value='1.2.3'
        )
        self.disk_format = DiskFormatVhdFixed(
            self.xml_state, 'root_dir', 'target_dir'
        )

    def test_post_init(self):
        self.disk_format.post_init({'option': 'value', '--tag': 'tag'})
        assert self.disk_format.options == [
            '-o', 'subformat=fixed', 'option', 'value'
        ]
        assert self.disk_format.tag == 'tag'

    @raises(KiwiVhdTagError)
    @patch('kiwi.storage.subformat.vhdfixed.Command.run')
    def test_create_image_format_invalid_tag(self, mock_command):
        self.disk_format.tag = 'invalid'
        self.disk_format.create_image_format()

    @patch('kiwi.storage.subformat.vhdfixed.Command.run')
    @patch_open
    def test_create_image_format(self, mock_open, mock_command):
        self.disk_format.tag = '12345678-1234-1234-1234-123456789999'
        context_manager_mock = mock.Mock()
        mock_open.return_value = context_manager_mock
        file_mock = mock.Mock()
        enter_mock = mock.Mock()
        exit_mock = mock.Mock()
        enter_mock.return_value = file_mock
        setattr(context_manager_mock, '__enter__', enter_mock)
        setattr(context_manager_mock, '__exit__', exit_mock)
        file_mock.read.return_value = 'dev_null_data'

        self.disk_format.create_image_format()

        mock_command.assert_called_once_with(
            [
                'qemu-img', 'convert', '-f', 'raw',
                'target_dir/some-disk-image.x86_64-1.2.3.raw', '-O', 'vpc',
                '-o', 'subformat=fixed',
                'target_dir/some-disk-image.x86_64-1.2.3.vhdfixed'
            ]
        )
        assert mock_open.call_args_list == [
            call('target_dir/some-disk-image.x86_64-1.2.3.vhdfixed', 'wb'),
            call('/dev/null', 'rb'),
            call('target_dir/some-disk-image.x86_64-1.2.3.vhdfixed', 'wb')
        ]
        assert file_mock.write.call_args_list[0] == call(
            'dev_null_data'
        )
        if sys.byteorder == 'little':
            # on little endian machines
            assert file_mock.write.call_args_list[1] == call(
                b'xV4\x124\x124\x12\x124\x124Vx\x99\x99'
            )
        else:
            # on big endian machines
            assert file_mock.write.call_args_list[1] == call(
                b'\x124Vx\x124\x124\x124\x124Vx\x99\x99'
            )
        assert file_mock.seek.call_args_list == [
            call(65536, 0), call(0, 2),
            call(65536, 0), call(0, 2)
        ]
