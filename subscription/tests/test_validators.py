from django.test import TestCase
from django.utils.module_loading import import_string

from subscription.validators import ImportCallBackValidator
from .utils import DUMMY_DOTTED_PATH


class ImportCallBackValidatorTestCase(TestCase):
    def setUp(self):
        super().setUp()
        self.validator = ImportCallBackValidator()
        self.dotted_path = DUMMY_DOTTED_PATH

    def test_validator_is_callable(self):
        self.assertTrue(callable(self.validator))

    def test_empty_dotted_path(self):
        self.assertIsNone(self.validator(''))

    def test_invalid_dotted_path(self):
        pass

    def test_valid_dotted_path(self):
        try:
            import_string(self.dotted_path)
        except ImportError:
            self.skipTest("Fix DUMMY_DOTTED_PATH to run this test!")

        self.assertIsNone(self.validator(self.dotted_path))

    def test_object_is_not_callable(self):
        pass

    def test_object_is_callable(self):
        pass
