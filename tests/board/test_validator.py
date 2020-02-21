import unittest
import datetime

from ddt import ddt, data, unpack

from board.manager import DefaultValidator

def generate_data(override=None, remove=None):
    data = {
        'owner': {
            'id': '12345', 'name': 'name',
        },
        'guild': {
            'id': '54321', 'name': 'team A',
        },
        'time': 1499794027,
    }
    if override:
        data.update(override)

    if remove:
        for key in remove:
            del data[key]

    return data

@ddt
class ValidatorTestCase(unittest.TestCase):

    def test_completely_clean_data(self):
        data = generate_data()
        cleaned = DefaultValidator.validate(data)
        self.assertEqual(cleaned, data)

    def test_int_data(self):
        data = generate_data({
            'owner': {
                'id': 12345, 'name': 'name',
            },
            'guild': {
                'id': 54321, 'name': 'team A',
            },
        })
        cleaned = DefaultValidator.validate(data)
        self.assertEqual(cleaned['owner']['id'], '12345')
        self.assertEqual(cleaned['guild']['id'], '54321')

    def test_long_data(self):
        toolongname = 't{} long name'.format('o'*100)
        data = generate_data({
            'owner': {
                'id': 12345, 'name': toolongname,
            },
        })
        cleaned = DefaultValidator.validate(data)
        self.assertTrue(toolongname, cleaned['owner']['name'])
        self.assertEqual(len(cleaned['owner']['name']), 32)

    @data(
        generate_data(remove=('owner',)),
        generate_data({'owner': None}),
        generate_data({'owner': {}}),
    )
    def test_required_fields(self, data):
        expected = 'owner.id must not be empty.'

        with self.assertRaises(ValueError) as cm:
            DefaultValidator.validate(data)
        self.assertEqual(cm.exception.args[0], expected)

    def test_time_aware(self):
        utc = datetime.datetime.fromisoformat("2017-07-11T17:27:07.299000+00:00")
        local = datetime.datetime.fromisoformat("2017-07-11T18:27:07.299000+01:00")
        self.assertEqual(utc, local)

        data = generate_data({'time': utc})
        cleaned = DefaultValidator.validate(data)
        self.assertEqual(cleaned['time'], int(utc.timestamp()))

        data = generate_data({'time': local})
        cleaned = DefaultValidator.validate(data)
        self.assertEqual(cleaned['time'], int(local.timestamp()))

    def test_time_naive_as_utc(self):
        naive = datetime.datetime.utcfromtimestamp(1499794027)
        self.assertIsNone(naive.tzinfo)

        data = generate_data({'time': naive})
        cleaned = DefaultValidator.validate(data)
        self.assertEqual(cleaned['time'], 1499794027)

    def test_time_int_epoch(self):
        data = generate_data({'time': 1499794027})
        cleaned = DefaultValidator.validate(data)
        self.assertEqual(cleaned['time'], 1499794027)

    def test_time_int_date(self):
        """It passed.  Applications must aware this behavior."""
        data = generate_data({'time': 20170711})
        cleaned = DefaultValidator.validate(data)
        self.assertEqual(cleaned['time'], 20170711)

        data = generate_data({'time': "20170711"})
        cleaned = DefaultValidator.validate(data)
        self.assertEqual(cleaned['time'], 20170711)

    def test_time_none(self):
        data = generate_data({'time': None})
        cleaned = DefaultValidator.validate(data)
        self.assertIsNotNone(cleaned['time'])

        data = generate_data(remove=('time',))
        cleaned = DefaultValidator.validate(data)
        self.assertIsNotNone(cleaned['time'])

    def test_time_str_invalid(self):
        data = generate_data({'time': 'Not a time'})
        with self.assertRaises(ValueError):
            cleaned = DefaultValidator.validate(data)
