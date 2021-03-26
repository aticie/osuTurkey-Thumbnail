from typing import Union
from io import BytesIO
from lzma import decompress as lzma_decompress

from utils.leb128 import Uleb128


class ReplayParser:

    def __init__(self, replay_file: Union[str, BytesIO]):
        if isinstance(replay_file, str):
            with open(replay_file, "rb") as replay:
                self.replay_raw = BytesIO(replay.read())
        else:
            self.replay_raw = replay_file

        self.replay_raw.seek(0)
        self.game_mode = int.from_bytes(self.replay_raw.read(1), byteorder="little")
        self.version = int.from_bytes(self.replay_raw.read(4), byteorder="little")
        self.beatmap_md5 = self.read_string()
        self.player_name = self.read_string()
        self.replay_md5 = self.read_string()
        self.count300 = int.from_bytes(self.replay_raw.read(2), byteorder="little")
        self.count100 = int.from_bytes(self.replay_raw.read(2), byteorder="little")
        self.count50 = int.from_bytes(self.replay_raw.read(2), byteorder="little")
        self.count_geki = int.from_bytes(self.replay_raw.read(2), byteorder="little")
        self.count_katu = int.from_bytes(self.replay_raw.read(2), byteorder="little")
        self.count_miss = int.from_bytes(self.replay_raw.read(2), byteorder="little")
        self.acc = self.calc_acc()
        self.score = int.from_bytes(self.replay_raw.read(4), byteorder="little")
        self.max_combo = int.from_bytes(self.replay_raw.read(2), byteorder="little")
        self.perfect = int.from_bytes(self.replay_raw.read(1), byteorder="little")
        self.mods = int.from_bytes(self.replay_raw.read(4), byteorder="little")
        self.parsed_mods = self.parse_mods()
        self.lifebar = self.read_string()
        self.timestamp = int.from_bytes(self.replay_raw.read(8), byteorder="little")
        self.compressed_data_length = int.from_bytes(self.replay_raw.read(4), byteorder="little")
        self.data = self.replay_raw.read(self.compressed_data_length)
        self.online_play_id = int.from_bytes(self.replay_raw.read(8), byteorder="little")

    def read_string(self):
        string_header = self.replay_raw.read(1)
        string = b""
        if string_header == b'\x0b':
            string_length = Uleb128(0).decode_from_stream(self.replay_raw, 'read', 1)
            string = self.replay_raw.read(string_length)

        return string.decode('utf-8')

    def get_frames(self):
        replay_frames = lzma_decompress(self.data).decode('utf-8').split(",")
        offset = int(replay_frames[1].split("|")[0]) + int(replay_frames[0].split("|")[0])
        replay_frames = [frame.split("|") for frame in replay_frames[2:-2]]

        time = offset
        absolute_frames = []
        times = []
        for frame in replay_frames:
            time += int(frame[0])
            if frame[0] == '0':
                absolute_frames.pop()
                times.pop()
            absolute_frames.append([time, float(frame[1]), float(frame[2]), int(frame[3])])
            times.append(time)

        return absolute_frames, times

    def dump_frames(self, file):
        readable_data = lzma_decompress(self.data).decode('utf-8')
        readable_data = readable_data.replace(",", "\n")
        with open(file, "w") as f:
            f.write(readable_data)

    def parse_mods(self):

        mod_dict = {v: k for k, v in {
            "NF": 1,
            "EZ": 2,
            "HD": 4,
            "HR": 5,
            "SD": 6,
            "DT": 7,
            "HT": 9,
            "NC": 10,
            "FL": 11}.items()}

        parsed_mods = []
        mod_int = 1
        for i in range(1, 12):
            if (mod_int & self.mods) == mod_int:
                parsed_mods.append(mod_dict[i])
            mod_int = mod_int << 1

        return parsed_mods

    def calc_acc(self):
        acc = ((self.count300 + self.count100 / 3 + self.count50 / 6) / (
                    self.count300 + self.count100 + self.count50 + self.count_miss)) * 100
        return acc
