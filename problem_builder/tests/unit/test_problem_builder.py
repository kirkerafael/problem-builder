import ddt
import unittest

from mock import MagicMock, Mock, patch
from random import random

from xblock.field_data import DictFieldData

from problem_builder.mcq import MCQBlock
from problem_builder.mentoring import (
    MentoringBlock, MentoringMessageBlock, _default_theme_config, _default_options_config
)


@ddt.ddt
class TestMentoringBlock(unittest.TestCase):
    def test_sends_progress_event_when_rendered_student_view_with_display_submit_false(self):
        block = MentoringBlock(MagicMock(), DictFieldData({
            'display_submit': False
        }), Mock())

        with patch.object(block, 'runtime') as patched_runtime:
            patched_runtime.publish = Mock()

            block.student_view(context={})

            patched_runtime.publish.assert_called_once_with(block, 'progress', {})

    def test_does_not_send_progress_event_when_rendered_student_view_with_display_submit_true(self):
        block = MentoringBlock(MagicMock(), DictFieldData({
            'display_submit': True
        }), Mock())

        with patch.object(block, 'runtime') as patched_runtime:
            patched_runtime.publish = Mock()

            block.student_view(context={})

            self.assertFalse(patched_runtime.publish.called)

    @ddt.data(True, False)
    def test_get_content_titles(self, has_title_set):
        """
        Test that we don't send a title to the LMS for the sequential's tooltips when no title
        is set
        """
        if has_title_set:
            data = {'display_name': 'Custom Title'}
            expected = ['Custom Title']
        else:
            data = {}
            expected = []
        block = MentoringBlock(MagicMock(), DictFieldData(data), Mock())
        self.assertEqual(block.get_content_titles(), expected)

    def test_does_not_crash_when_get_child_is_broken(self):
        block = MentoringBlock(MagicMock(), DictFieldData({
            'children': ['invalid_id'],
        }), Mock())

        with patch.object(block, 'runtime') as patched_runtime:
            patched_runtime.publish = Mock()
            patched_runtime.service().ugettext = lambda str: str
            patched_runtime.get_block = lambda block_id: None
            patched_runtime.load_block_type = lambda block_id: Mock

            fragment = block.student_view(context={})

            self.assertIn('Unable to load child component', fragment.content)


class TestMentoringBlockTheming(unittest.TestCase):
    def setUp(self):
        self.service_mock = Mock()
        self.runtime_mock = Mock()
        self.runtime_mock.service = Mock(return_value=self.service_mock)
        self.block = MentoringBlock(self.runtime_mock, DictFieldData({}), Mock())

    def test_student_view_calls_include_theme_files(self):
        self.service_mock.get_settings_bucket = Mock(return_value={})
        with patch.object(self.block, 'include_theme_files') as patched_include_theme_files:
            fragment = self.block.student_view({})
            patched_include_theme_files.assert_called_with(fragment)

    def test_author_preview_view_calls_include_theme_files(self):
        self.service_mock.get_settings_bucket = Mock(return_value={})
        with patch.object(self.block, 'include_theme_files') as patched_include_theme_files:
            fragment = self.block.author_preview_view({})
            patched_include_theme_files.assert_called_with(fragment)


@ddt.ddt
class TestMentoringBlockOptions(unittest.TestCase):
    def setUp(self):
        self.service_mock = Mock()
        self.runtime_mock = Mock()
        self.runtime_mock.service = Mock(return_value=self.service_mock)
        self.block = MentoringBlock(self.runtime_mock, DictFieldData({}), Mock())

    def test_get_options_returns_default_if_xblock_settings_not_customized(self):
        self.block.get_xblock_settings = Mock(return_value=None)
        self.assertEqual(self.block.get_options(), _default_options_config)
        self.block.get_xblock_settings.assert_called_once_with(_default_options_config)

    @ddt.data(
        {}, {'mass': 123}, {'spin': {}}, {'parity': "1"}
    )
    def test_get_options_returns_default_if_options_not_customized(self, xblock_settings):
        self.block.get_xblock_settings = Mock(return_value=xblock_settings)
        self.assertEqual(self.block.get_options(), _default_options_config)
        self.block.get_xblock_settings.assert_called_once_with(_default_options_config)

    @ddt.data(
        {MentoringBlock.options_key: 123},
        {MentoringBlock.options_key: [1, 2, 3]},
        {MentoringBlock.options_key: {'pb_mcq_hide_previous_answer': False}},
     )
    def test_get_options_correctly_returns_customized_options(self, xblock_settings):
        self.block.get_xblock_settings = Mock(return_value=xblock_settings)
        self.assertEqual(self.block.get_options(), xblock_settings[MentoringBlock.options_key])
        self.block.get_xblock_settings.assert_called_once_with(_default_options_config)

    def test_get_option(self):
        random_key, random_value = random(), random()
        with patch.object(self.block, 'get_options') as patched_get_options:
            patched_get_options.return_value = {random_key: random_value}
            option = self.block.get_option(random_key)
            patched_get_options.assert_called_once_with()
            self.assertEqual(option, random_value)

    def test_student_view_calls_get_option(self):
        self.service_mock.get_settings_bucket = Mock(return_value={})
        with patch.object(self.block, 'get_option') as patched_get_option:
            self.block.student_view({})
            patched_get_option.assert_called_with('pb_mcq_hide_previous_answer')


class TestMentoringBlockJumpToIds(unittest.TestCase):
    def setUp(self):
        self.service_mock = Mock()
        self.runtime_mock = Mock()
        self.runtime_mock.service = Mock(return_value=self.service_mock)
        self.block = MentoringBlock(self.runtime_mock, DictFieldData({'mode': 'assessment'}), Mock())
        self.block.children = ['dummy_id']
        self.message_block = MentoringMessageBlock(
            self.runtime_mock, DictFieldData({'type': 'bogus', 'content': 'test'}), Mock()
        )
        self.block.runtime.replace_jump_to_id_urls = lambda x: x.replace('test', 'replaced-url')

    def test_get_message_content(self):
        with patch('problem_builder.mixins.child_isinstance') as mock_child_isinstance:
            mock_child_isinstance.return_value = True
            self.runtime_mock.get_block = Mock()
            self.runtime_mock.get_block.return_value = self.message_block
            self.assertEqual(self.block.get_message_content('bogus'), 'replaced-url')

    def test_get_tip_content(self):
        self.mcq_block = MCQBlock(self.runtime_mock, DictFieldData({'name': 'test_mcq'}), Mock())
        self.mcq_block.get_review_tip = Mock()
        self.mcq_block.get_review_tip.return_value = self.message_block.content
        self.block.step_ids = []
        self.block.steps = [self.mcq_block]
        self.block.student_results = {'test_mcq': {'status': 'incorrect'}}
        self.assertEqual(self.block.review_tips, ['replaced-url'])

    def test_get_tip_content_no_tips(self):
        self.mcq_block = MCQBlock(self.runtime_mock, DictFieldData({'name': 'test_mcq'}), Mock())
        self.mcq_block.get_review_tip = Mock()
        # If there are no review tips, get_review_tip will return None;
        # simulate this situation here:
        self.mcq_block.get_review_tip.return_value = None
        self.block.step_ids = []
        self.block.steps = [self.mcq_block]
        self.block.student_results = {'test_mcq': {'status': 'incorrect'}}
        try:
            review_tips = self.block.review_tips
        except TypeError:
            self.fail('Trying to replace jump_to_id URLs in non-existent review tips.')
        else:
            self.assertEqual(review_tips, [])