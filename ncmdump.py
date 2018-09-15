# -*- coding: utf-8 -*-
import binascii
import struct
import base64
import json
import os
from Crypto.Cipher import AES
from mutagen import mp3, flac, id3

SPECIAL_FORMAT = '<I'

UTF_8 = 'utf-8'

CONVERT_FOLDER = 'convert'
PARENT_FOLDER = 'F:/eCloudMusic/'
FORMAT = 'format'
TITLE = 'title'
ALBUM = 'album'
ARTIST = 'artist'
MUSIC_NAME = 'musicName'
FLAC_TYPE = 'flac'
MP3_TYPE = 'mp3'
JPEG_MINE = 'image/jpeg'


def un_pad(s):
    return s[0:-(s[-1] if type(s[-1]) == int else ord(s[-1]))]


def dump(file_path):

    core_key = binascii.a2b_hex("687A4852416D736F356B496E62617857")
    meta_key = binascii.a2b_hex("2331346C6A6B5F215C5D2630553C2728")

    f = open(file_path, 'rb')

    # magic header
    header = f.read(8)
    assert binascii.b2a_hex(header) == b'4354454e4644414d'

    # key data
    f.seek(2, 1)
    key_length = f.read(4)
    key_length = struct.unpack(SPECIAL_FORMAT, bytes(key_length))[0]

    key_data = bytearray(f.read(key_length))
    key_data = bytes(bytearray([byte ^ 0x64 for byte in key_data]))

    crypter = AES.new(core_key, AES.MODE_ECB)
    key_data = un_pad(crypter.decrypt(key_data))[17:]
    key_length = len(key_data)

    # key box
    key_data = bytearray(key_data)
    key_box = bytearray(range(256))
    j = 0

    for i in range(256):
        j = (key_box[i] + j + key_data[i % key_length]) & 0xff
        key_box[i], key_box[j] = key_box[j], key_box[i]

    # meta data
    meta_length = f.read(4)
    meta_length = struct.unpack(SPECIAL_FORMAT, bytes(meta_length))[0]

    meta_data = bytearray(f.read(meta_length))
    meta_data = bytes(bytearray([byte ^ 0x63 for byte in meta_data]))
    meta_data = base64.b64decode(meta_data[22:])

    crypter = AES.new(meta_key, AES.MODE_ECB)
    meta_data = un_pad(crypter.decrypt(meta_data)).decode(UTF_8)[6:]

    meta_data = json.loads(meta_data)

    # crc32
    f.read(4)
    # struct.unpack(SPECIAL_FORMAT, bytes(crc32))[0]

    # album cover
    f.seek(5, 1)
    image_size = f.read(4)
    image_size = struct.unpack(SPECIAL_FORMAT, bytes(image_size))[0]
    image_data = f.read(image_size)

    # media data
    file_name = meta_data[ARTIST][0][0] + ' - ' + meta_data[MUSIC_NAME] + '.' + meta_data[FORMAT]
    file_name = file_name.replace('"', '')
    music_path = os.path.join(CONVERT_FOLDER, os.path.split(file_path)[0], file_name)

    if not os.path.exists(CONVERT_FOLDER):
        os.makedirs(CONVERT_FOLDER)

    if os.path.exists(music_path):
        return

    m = open(music_path, 'wb')

    while True:
        chunk = bytearray(f.read(0x8000))
        chunk_length = len(chunk)
        if not chunk:
            break

        for i in range(chunk_length):
            j = (i + 1) & 0xff
            chunk[i] ^= key_box[(key_box[j] + key_box[(key_box[j] + j) & 0xff]) & 0xff]

        m.write(chunk)

    m.close()
    f.close()

    method_name(image_data, meta_data, music_path)


def method_name(image_data, meta_data, music_path):
    audio = []
    # media tag
    if meta_data[FORMAT] == FLAC_TYPE:
        audio = flac.FLAC(music_path)
        image = flac.Picture()
        image.type = 3
        image.mime = JPEG_MINE
        image.data = image_data
        audio.clear_pictures()
        audio.add_picture(image)
    elif meta_data[FORMAT] == MP3_TYPE:
        audio = mp3.MP3(music_path)
        image = id3.APIC()
        image.type = 3
        image.mime = JPEG_MINE
        image.data = image_data
        audio.tags.add(image)
        audio.save()
        audio = mp3.EasyMP3(music_path)

    audio[TITLE] = meta_data[MUSIC_NAME]
    audio[ALBUM] = meta_data[ALBUM]
    audio[ARTIST] = os.altsep.join([artist[0] for artist in meta_data[ARTIST]])
    audio.save()


if __name__ == '__main__':
    import sys
    os.chdir(PARENT_FOLDER)
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = [file_name for file_name in os.listdir('.') if os.path.splitext(file_name)[-1] == '.ncm']

    if not files:
        print('please input file path!')
        
    for file_name in files:
        try:
            dump(file_name)
            print(os.path.split(file_name)[-1])
        except Exception as e:
            print(e.__cause__)
            pass
