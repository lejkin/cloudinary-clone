from ImageProcessor import ImageProcessor
import json, sys
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


#terminal collors
class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


## remove actual files
shutil.rmtree("output")
os.mkdir("output")


## get list of parameters test
try:
    with open('presets.json') as f:
        PRESETS = json.load(f)
except Exception as error:
    print(error)
    sys.exit(1)



## convert all files from parameters present in presets.json
for image_filename in glob.iglob('images/*'):
    print(image_filename)
    for present in PRESETS:
        try:
            #print present, PRESETS[present]

            p = ImageProcessor('./{}'.format(image_filename) )
            buff = p.process(parse_options(PRESETS[present]))

            output_filename = "output/" + present + "_" + str(image_filename.split('/')[-1])

            with open(output_filename ,'wb') as output:
                output.write(buff.getvalue())

            print(bcolors.OKGREEN, 'success', image_filename, present, bcolors.ENDC)

        except Exception as error:
            print(bcolors.FAIL, 'error', image_filename, present, error, bcolors.ENDC)




