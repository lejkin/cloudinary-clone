import unittest

from ImageProcessor import ImageProcessor
import json
import shutil, os
import glob


def parse_options(raw_options):
    options = {}
    opts_list = raw_options.split(',')
    for opt in opts_list:
        k, w = opt.split('_', 1)
        if '_' in w:
            opts = w.split('_')
        else:
            opts = w
        options[k] = opts
    return options


class ConversionTest(unittest.TestCase):
    def setUp(self):
        shutil.rmtree("output", ignore_errors=True)
        os.mkdir("output")

        with open('presets.json') as f:
            self.PRESETS = json.load(f)

        self.images = glob.iglob('images/*')

    def test_convert(self):
        """
        Test that images converted as expected and saved w/o errors
        """
        for image_filename in self.images:
            for present in self.PRESETS:
                with self.subTest(name='{}: {}'.format(image_filename, present)):
                    p = ImageProcessor('./{}'.format(image_filename))
                    buff = p.process(parse_options(self.PRESETS[present]))

                    output_filename = "output/{}_{}".format(present, image_filename.split('/')[-1])

                    with open(output_filename, 'wb') as output:
                        output.write(buff.getvalue())
                    assert os.path.exists(output_filename) and os.path.getsize(
                        output_filename) > 0, 'Image is empty or not saved'


if __name__ == '__main__':
    unittest.main()
