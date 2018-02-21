from PIL import Image, ImageDraw, ImageOps
from io import BytesIO
import webcolors
import face_recognition


DOWNSCALE = Image.ANTIALIAS

class ImageProcessor:
    """
    x_355
    y_410
    c_pad,
    g_center,
    bo_1px_solid_white,
    q_100, q_90
    c_thumb
    g_face
    r_max
    """

    def __init__(self, path):
        self.path = path
        self.im = Image.open(self.path)
        self.format = self.im.format

    def process(self, options):
        self.set_width(options)
        self.set_height(options)

        if self.w is None and self.h is None:
            self.w, self.h = self.im.size
        elif self.w is None:
            self.w = int(self.h * (self.im.width / self.im.height))
        elif self.h is None:
            self.h = int(self.w * (self.im.height / self.im.width))
        self.set_gravity(options)

        self.op_crop(options)

        buff = BytesIO()
        kw = {}
        quality = int(options.get('q', 100))
        if self.format == 'JPEG':
            kw['quality'] = quality
            self.im = self.im.convert('RGB')
            self.im.save(buff, self.format, **kw)
        elif self.format == 'PNG':
            background = Image.new("RGB", self.im.size, (250, 250, 250))
            channels = self.im.split()
            background.paste(self.im, mask=channels[3] if len(channels) > 3 else None) # 3 is the alpha channel
            self.format = 'JPEG'
            kw['quality'] = quality
            background.save(buff, self.format, **kw)

            #kw['compress_level'] = max(0, 9 - quality // 11)
        #self.im.save(buff, self.format, **kw)
        buff.seek(0)
        return buff

    def set_gravity(self, options):
        self.g = self.im.size[0] / 2, self.im.size[1] / 2
        self.cx = self.im.width // 2
        self.cy = self.im.height // 2
        self.delta_x = min(self.im.width // 2, self.im.height // 2)
        self.delta_y = self.delta_x

    def set_width(self, options):
        w = options.get('w', '')
        try:
            self.w = int(w)
            return
        except ValueError:
            pass
        try:
            self.w = float(w) * self.im.size[0]
            return
        except ValueError:
            pass
        self.w = None

    def set_height(self, options):
        h = options.get('h', '')
        try:
            self.h = int(h)
            return
        except ValueError:
            pass
        try:
            self.h = float(h) * self.im.size[1]
            return
        except ValueError:
            pass
        self.h = None

    def set_background(self):
        pass

    def op_crop(self, options):
        if options.get('g') == 'face':
            fr_image = face_recognition.load_image_file(self.path, mode='RGB')
            face_locations = face_recognition.face_locations(fr_image)
            if face_locations:
                box = self.face_box_to_image_box(face_locations[0])
                face_center_x = box[0] + (box[2] - box[0])//2
                face_center_y = box[1] + (box[3] - box[1])//2
                self.cx = face_center_x
                self.cy = face_center_y
                self.face_box = box
                face_box_w = box[2] - box[0]
                face_box_h = box[3] - box[1]
                self.delta_x = face_box_w // 2
                self.delta_y = face_box_h // 2
        if options.get('c') == 'thumb':
            ar = self.w / self.h

            crop_box = (self.cx - self.delta_x * ar, self.cy - self.delta_y / ar, self.cx + self.delta_x * ar, self.cy + self.delta_y / ar)
            self.im = self.im.crop(crop_box)
            factor = max(self.w / self.im.width, self.h / self.im.height)
            w = int(self.im.width * factor)
            h = int(self.im.height * factor)
            self.im = self.im.resize((w, h), DOWNSCALE)
        elif options.get('c') == 'fill':
            ar = self.w / self.h
            size = (self.w, self.h)
            bg = Image.new('RGBA', size, (255, 255, 255, 0))
            factor = min(self.im.width / float(self.w), self.im.height / float(self.h))
            w = int(self.im.width / factor)
            h = int(self.im.height / factor)
            self.im = self.im.resize((w, h), DOWNSCALE)
            bg.paste(self.im, ((self.w - self.im.width) // 2, (self.h - self.im.height) // 2))
            self.im = bg
        elif options.get('c') == 'pad':
            ar = self.w / self.h
            size = (self.w, self.h)
            bg = Image.new('RGBA', size, (255, 255, 255, 0))
            factor = max(self.im.width / float(self.w), self.im.height / float(self.h))
            w = int(self.im.width / factor)
            h = int(self.im.height / factor)
            self.im = self.im.resize((w, h), DOWNSCALE)
            bg.paste(self.im, ((self.w - self.im.width) // 2, (self.h - self.im.height) // 2))
            self.im = bg
        else:
            self.im = self.im.resize((self.w, self.h), DOWNSCALE)
        if options.get('r') == 'max':
            im = self.im
            w, h = im.size
            rad = 50
            circle = Image.new('L', im.size, 0)
            draw = ImageDraw.Draw(circle)
            draw.ellipse((0, 0, w, h), fill=255)
            alpha = Image.new('L', im.size, 255)
            rad_x = int(w / 2)
            rad_y = int(h / 2)
            alpha.paste(circle.crop((0, 0, rad_x, rad_y)), (0, 0))
            alpha.paste(circle.crop((0, rad_y, rad_x, h)), (0, rad_y))
            alpha.paste(circle.crop((rad_x, 0, w, rad_y)), (rad_x, 0))
            alpha.paste(circle.crop((rad_x, rad_y, w, h)), (rad_x, rad_y))
            im.putalpha(alpha)

            if options.get('bo'):
                bwidth, bstyle, bcolor = options['bo']
                border_width = int(bwidth.replace('px', ''))
                border_color = webcolors.name_to_rgb(bcolor)
                mask = Image.new('L', (w, h), 0)
                mask_draw = ImageDraw.Draw(mask)
                mask_draw.ellipse((0, 0, im.size[0], im.size[1]), fill=255)

                brd = Image.new('RGBA', (w + border_width * 2, h + border_width * 2), 0)
                draw = ImageDraw.Draw(brd)
                draw.ellipse((0, 0, brd.size[0], brd.size[1]), fill=border_color)
                brd.paste(im, (border_width, border_width), mask)
                self.im = brd

    def face_box_to_image_box(self, face_box):
        b = face_box
        fact = 0.35
        y_fact = 0.2
        x_pad = (b[1] - b[3]) * fact
        y_pad = (b[2] - b[0]) * fact
        eyes_y_pad = (b[2] - b[0]) * y_fact
        x0 = max(0, b[3] - x_pad)
        y0 = max(0, b[0] - y_pad - eyes_y_pad)
        x1 = min(self.im.width, b[1] + x_pad)
        y1 = min(self.im.height, b[2] + y_pad - eyes_y_pad)
        return (x0, y0, x1, y1)
