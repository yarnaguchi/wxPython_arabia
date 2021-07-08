import wx
import sys
import os
import random
import json
import codecs
import time
import threading
import re
from datetime import datetime

from src import arabic
from src import arabic_original


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, "_MEIPASS"):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class MainFrame(wx.Frame):
    def __init__(self):
        super().__init__(
            parent=None,
            title='アラビア変換テスト',
            # style=wx.DEFAULT_FRAME_STYLE & ~(wx.RESIZE_BORDER | wx.MAXIMIZE_BOX)
        )
        self.SetBackgroundColour('Alpha')

        sizer = wx.BoxSizer(orient=wx.VERTICAL)

        input_panel = InputPanel(parent=self)
        sizer.Add(window=input_panel, flag=wx.ALIGN_LEFT | wx.TOP | wx.RIGHT | wx.LEFT | wx.GROW, border=10)

        result_panel = ResultPanel(parent=self)
        sizer.Add(result_panel, flag=wx.ALIGN_LEFT | wx.TOP | wx.RIGHT | wx.LEFT | wx.GROW, border=10, proportion=1)

        button_panel = ButtonPanel(parent=self)
        sizer.Add(window=button_panel, flag=wx.ALIGN_RIGHT)

        self.SetSizer(sizer=sizer)

        icon = wx.Icon()
        # BITMAP_TYPE_JPEGにすれば、JPEGも読める
        icon_source = wx.Image(name=resource_path('icon_wst_64px.ico'), type=wx.BITMAP_TYPE_ICO)
        icon.CopyFromBitmap(icon_source.ConvertToBitmap())
        self.SetIcon(icon)

        command = Commands(input_panel.speaker_objs, button_panel, result_panel)
        command.clear(event=None)
        sizer.Fit(self)


class InputPanel(wx.Panel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.speaker_objs = []
        for speaker in range(1, num_of_speakers + 1):
            self.speaker_objs.append(SpeakerPanel(label="話者" + str(speaker), parent=self))

        sizer = wx.GridSizer(rows=1, cols=2, gap=wx.Size(5, 1))

        for obj in self.speaker_objs:
            sizer.Add(obj, flag=wx.ALIGN_RIGHT | wx.TOP | wx.RIGHT | wx.LEFT | wx.GROW, border=10)
        self.SetSizer(sizer=sizer)
        sizer.Fit(self)


class SpeakerPanel(wx.Panel):
    def __init__(self, label="", *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.input_panel = LatticeDataPanel(parent=self)
        self.output_panel = LatticeDataPanel(parent=self)

        sizer = wx.StaticBoxSizer(parent=self, orient=wx.HORIZONTAL, label=label)
        for obj in [self.input_panel, self.output_panel]:
            sizer.Add(obj, flag=wx.ALIGN_CENTER | wx.RIGHT | wx.LEFT | wx.GROW, border=10, proportion=1)
        self.SetSizer(sizer=sizer)
        sizer.Fit(self)


class LatticeDataPanel(wx.Panel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.headers = ["", "start", "end", "word"]
        labels = ["word" + str(x + 1) for x in range(num_of_rows)]

        self.text_ctrls = {}
        for row in range(num_of_rows):
            for i, header in enumerate([x for x in self.headers if x]):
                if i == 0 or i == 1:
                    size = wx.Size(width=40, height=-1)
                else:
                    size = wx.DefaultSize

                if row in self.text_ctrls:
                    self.text_ctrls[row].update({header: wx.TextCtrl(parent=self, size=size)})
                else:
                    self.text_ctrls.setdefault(row, {header: wx.TextCtrl(parent=self, size=size)})

        sizer = wx.FlexGridSizer(
            rows=len(labels) + 1,
            cols=len(self.headers),
            gap=wx.Size(5, 1)
        )

        for header in self.headers:
            sizer.Add(window=wx.StaticText(parent=self, label=header), flag=wx.ALIGN_CENTER)

        for i, label in enumerate(labels):
            sizer.Add(window=wx.StaticText(parent=self, label=label), flag=wx.ALIGN_LEFT)

            for header in [x for x in self.headers if x]:
                sizer.Add(window=self.text_ctrls[i][header], flag=wx.ALIGN_CENTER | wx.EXPAND)

        # sizer.AddGrowableRow(0)
        sizer.AddGrowableCol(3)
        self.SetSizer(sizer=sizer)
        sizer.Fit(self)


class ButtonPanel(wx.Panel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.execute_button = wx.Button(parent=self, id=1111, label='変換')
        self.clear_button = wx.Button(parent=self, id=2222, label='クリア')
        self.random_button = wx.Button(parent=self, id=3333, label='ランダム')
        # self.file_button = wx.Button(parent=self, id=4444, label='jsonファイルを\n読み込む')
        self.folder_button = wx.Button(parent=self, id=5555, label='jsonフォルダを\n読み込む')

        sizer = wx.BoxSizer(orient=wx.HORIZONTAL)

        for obj in [self.execute_button, self.clear_button, self.random_button,
                    # self.file_button,
                    self.folder_button]:
            sizer.Add(window=obj, flag=wx.EXPAND | wx.RIGHT, border=4)
        self.SetSizer(sizer=sizer)


class ResultPanel(wx.Panel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        sizer = wx.BoxSizer(orient=wx.HORIZONTAL)
        self.result = wx.TextCtrl(parent=self, style=wx.TE_MULTILINE, size=wx.Size(-1, 200))
        sizer.Add(window=self.result, proportion=1, flag=wx.ALIGN_CENTER | wx.EXPAND)
        self.SetSizer(sizer=sizer)
        sizer.Fit(self)


class Commands(object):
    def __init__(self, *args, **kwargs):
        self.speaker_obj, self.button_panel, self.result_panel = args[0], args[1], args[2]

        self.button_panel.execute_button.Bind(wx.EVT_BUTTON, self.execute)
        self.button_panel.clear_button.Bind(wx.EVT_BUTTON, self.clear)
        self.button_panel.random_button.Bind(wx.EVT_BUTTON, self.random)
        # self.button_panel.file_button.Bind(wx.EVT_BUTTON, self.file_load)
        self.button_panel.folder_button.Bind(wx.EVT_BUTTON, self.folder_load)

        self.bind()

        self.loop_on = False

        self.result_panel.result.Bind(wx.EVT_KEY_DOWN, self.check_key)
        self.trans = arabic.Kansuji2Arabic()
        self.trans_original = arabic_original.Kansuji2Arabic()

    def bind(self):
        return
        for row in range(num_of_rows):
            for speaker_obj in self.speaker_obj:
                for header in [x for x in speaker_obj.input_panel.headers if x]:
                    speaker_obj.input_panel.text_ctrls[row][header].Bind(event=wx.EVT_TEXT, handler=self.execute)

    def unbind(self):
        return
        for row in range(num_of_rows):
            for speaker_obj in self.speaker_obj:
                for header in [x for x in speaker_obj.input_panel.headers if x]:
                    speaker_obj.input_panel.text_ctrls[row][header].Unbind(event=wx.EVT_TEXT)

    def pass_event(self, event):
        pass

    def check_key(self, event):
        def loop():
            keycode = event.GetKeyCode()
            if keycode == wx.WXK_RETURN:
                while self.loop_on:
                    self.random()
                    time.sleep(0.1)
        if self.loop_on:
            self.loop_on = False
        else:
            self.loop_on = True
        t = threading.Thread(target=loop)
        t.start()

    def execute(self, event):
        # if not event.GetId() == 1111:
        #     return

        self.unbind()

        lattice = {}
        for speaker in range(1, len(self.speaker_obj) + 1):
            lattice.setdefault(str(speaker), {})

        for speaker, speaker_obj in enumerate(self.speaker_obj):
            for k, v in speaker_obj.input_panel.text_ctrls.items():
                tmp = {
                        "start": 0.0,
                        "end": 0.1,
                        "weight": 0,
                        "best_path": True,
                        "speaker": speaker + 1,
                        "word": "",
                        "intensity": 0
                    }

                for header in [x for x in speaker_obj.input_panel.headers if x]:
                    tmp[header] = v[header].GetValue()
                    if str(k) in lattice[str(speaker + 1)]:
                        lattice[str(speaker + 1)][str(k)].update(tmp)
                    else:
                        lattice[str(speaker + 1)].setdefault(str(k), tmp)

        self.result_panel.result.SetValue(self.lattice2csv(lattice))
        self.result_panel.result.AppendText("\n\n")

        # lattice = self.trans.execute(lattice, [], force_trans=False)
        lattice = self.trans_original.execute(lattice, [], force_trans=False)

        for speaker, speaker_obj in enumerate(self.speaker_obj):
            for k, v in speaker_obj.output_panel.text_ctrls.items():
                for header in [x for x in speaker_obj.output_panel.headers if x]:
                    v[header].Clear()
                    v[header].Enable()
                    if (str(k) in lattice[str(speaker + 1)]
                            and lattice[str(speaker + 1)][str(k)]["word"] not in ["!NULL", "!ENTER", "!EXIT"]):
                        v[header].SetValue(lattice[str(speaker + 1)][str(k)][header])
                    else:
                        v[header].SetValue(lattice[str(speaker + 1)][str(k)][header])
                        v[header].Disable()

        # WriteTextだと右側に追加
        self.result_panel.result.AppendText(self.lattice2csv(lattice))

        self.bind()

    def clear(self, *args, **kwargs):
        self.loop_on = False
        self.unbind()

        # 入力欄のクリア
        for speaker, speaker_obj in enumerate(self.speaker_obj):
            for k, v in speaker_obj.input_panel.text_ctrls.items():
                for i, header in enumerate([x for x in speaker_obj.input_panel.headers if x]):
                    if i == 0 or i == 1:
                        v[header].SetValue(str(speaker + (i + k)/10))
                    else:
                        v[header].Clear()

        # 出力欄のクリア
        for speaker_obj in self.speaker_obj:
            for k, v in speaker_obj.output_panel.text_ctrls.items():
                for header in [x for x in speaker_obj.input_panel.headers if x]:
                    v[header].Enable()
                    v[header].Clear()

        self.result_panel.result.Clear()

        # フォーカスを先頭行の単語にセット
        self.speaker_obj[0].input_panel.text_ctrls[0]["word"].SetFocus()

        self.bind()

    def random(self, *args, **kwargs):  # , event):
        # if not event.GetId() == 3333:
        #     return
        self.unbind()

        sample = []
        for x in '０１２３４５６７８９' \
                 '一二三四五六七八九〇零十百千万':
                 # '一二三四五六七八九〇零十百千点、点、点、万億兆億万兆月分日時秒':
                 # 'あいうえおかきくけこさしすせそたちつてと':
                 # 'なにぬねのはひふへほまみむめもやゆよらり' \
                 # 'るれろわをんがぎぐげござじずぜぞだぢづでど' \
                 # 'ばびぶべぼぱぴぷぺぽぁぃぅぇぉゃゅょっ':
            sample.append(x)

        for speaker_obj in self.speaker_obj:
            for k, v in speaker_obj.input_panel.text_ctrls.items():
                word = ""
                word_length = random.choice([1, 2, 3, 4])
                if word_length == 1:
                    word += random.choice([x for x in "一二三四五六七八九〇零十百千万億兆点、"] + ["!NULL"])
                else:
                    for i in range(word_length):
                        word += random.choice(sample)
                v[speaker_obj.input_panel.headers[3]].SetValue(word)

        self.execute(event=None)
        self.bind()

    def file_load(self, event):
        if not event.GetId() == 4444:
            return

        dlg = wx.FileDialog(parent=frame,
                            message="ファイルを選択してください",
                            defaultDir=".",
                            defaultFile="",
                            wildcard="テキストファイル(*.txt)|*.txt|"
                                     "jsonファイル(*.json)|*.json|"
                                     "全てのファイル(*.*)|*.*",
                            style=wx.FD_FILE_MUST_EXIST)
        dlg.ShowModal()
        input_file = dlg.GetPath()

        if not input_file:
            return

        path, extention = os.path.splitext(input_file)

        # print(os.path.dirname(input_file))  # C:\Users\tsumura\Desktop\NTE Client\client_data
        # print(os.path.basename(input_file))  # 0000_01_01_20161026_155134_0001.wav.txt
        # print(os.path.split(input_file))  # ('C:\\Users\\tsumura\\Desktop\\NTE Client\\client_data', '0000_01_01_20161026_155134_0001.wav.txt')
        # print(os.path.splitext(input_file))  # ('C:\\Users\\tsumura\\Desktop\\NTE Client\\client_data\\0000_01_01_20161026_155134_0001.wav', '.txt')

        lattice = None
        error = False
        with open(input_file, mode="r", encoding="utf-8") as f:
            json_data = json.load(f)
        try:
            lattice, keywords = self.trans.tr_edit_lattice(json_data)
        except Exception:
            dialog = wx.MessageDialog(parent=frame,
                                      message='jsonファイルが不正です',
                                      caption='エラー',
                                      style=wx.ICON_ERROR)
            dialog.ShowModal()
            dialog.Destroy()
            error = True

        if not error:
            self.file_output(self.lattice2csv(lattice), path + ".csv")
            lattice = self.trans.execute(lattice)
            self.file_output(self.lattice2csv(lattice), path + "(arabia).csv")

            dialog = wx.MessageDialog(parent=frame,
                                      message="選択したjsonファイルと同じフォルダに\n ・" +
                                              os.path.basename(path + ".csv") + "\n ・" +
                                              os.path.basename(path + "(arabia).csv") +
                                              "\nを出力しました",
                                      caption='jsonファイル処理完了',
                                      style=wx.OK)
            dialog.ShowModal()
            dialog.Destroy()

    def folder_load(self, event):
        if not event.GetId() == 5555:
            return

        output_folder = "output_" + datetime.now().strftime("%Y%m%d%H%M%S")

        word = "一二三四五六七八九〇零十百千\d点、."
        target_list = re.compile('[' + word + ']')

        folder = wx.DirDialog(
            parent=frame,
            message="jsonファイルがあるフォルダを選択",
            style=wx.DD_CHANGE_DIR,
            )

        result = {}
        input_files = []
        lattice = None
        input_folder = ""
        if folder.ShowModal() == wx.ID_OK:
            input_folder = folder.GetPath()
            input_files = os.listdir(input_folder)
        folder.Destroy()

        if not input_folder:
            return

        for input_file in input_files:
            extention = os.path.splitext(input_file)[1]
            outputpath = os.path.join(input_folder, output_folder, os.path.splitext(input_file)[0])
            if not os.path.exists(os.path.join(input_folder, output_folder)):
                os.makedirs(os.path.join(input_folder, output_folder))

            if extention not in [".txt", ".json"]:
                continue
            with open(input_file, mode="r", encoding="utf-8") as f:
                try:
                    json_data = json.load(f)
                    lattice, keywords = self.trans.tr_edit_lattice(json_data)
                except Exception as err:
                    print(input_file + "でエラー(" + str(err) + ")")
                    continue

            self.file_output(self.lattice2csv(lattice), outputpath + ".csv")

            lattice1 = self.trans_original.execute(lattice, [], force_trans=False)
            self.file_output(self.lattice2csv(lattice1), outputpath + "(arabia1).csv")

            # lattice2 = self.trans.execute(lattice, [], force_trans=False)
            # self.file_output(self.lattice2csv(lattice2), outputpath + "(arabia2).csv")
            #
            lattice3 = self.trans_original.execute(lattice, [], force_trans=True)
            self.file_output(self.lattice2csv(lattice3), outputpath + "(force_arabia).csv")

            result = {}
            tag = ""
            for ext in [".csv", "(arabia1).csv", "(force_arabia).csv"]:  # , "(arabia2).csv"]:
                with codecs.open(outputpath + ext, "r", "utf-8-sig") as f:
                    if ext == ".csv":
                        # continue
                        tag = "4.アラビア変換無し"
                    elif ext == "(arabia1).csv":
                        # continue
                        tag = "1.アラビア変換－１"
                    # elif ext == "(arabia2).csv":
                    #     # continue
                    #     tag = "2.アラビア変換－２"
                    elif ext == "(force_arabia).csv":
                        # continue
                        tag = "3.強制アラビア変換"
                    for i, line in enumerate(f):
                        if i > 0 and len(target_list.findall(line.split(",")[2])) > 0:
                            if input_file not in result:
                                result.setdefault(input_file, [])
                            data = line.split(",")
                            result[input_file].append([float(data[0])] +
                                                      [data[1]] +
                                                      [tag] +
                                                      data[-1:])

            for file, data in result.items():
                result[file].sort()

            before_data0 = ""
            for file, datas in result.items():
                for data in datas:
                    if before_data0 != str(data[0]):
                        data[0] = str(data[0])
                        before_data0 = str(data[0])
                    else:
                        data[0] = ""

            with codecs.open(os.path.join(output_folder, "result.csv"), "a", "utf-8-sig") as o:
                for file, data in result.items():
                    o.write(file + "\n")
                    for x in data:
                        o.write(", ".join(x))
                o.write("\n")

        dialog = wx.MessageDialog(parent=frame,
                                  message="フォルダ" + output_folder + "にファイルを出力しました。" +
                                          "\nresult.csvを参照してください。",
                                  caption='jsonファイル処理完了',
                                  style=wx.OK)
        dialog.ShowModal()
        dialog.Destroy()

    def lattice2csv(self, lattice):
        transcription_result = []

        for speaker in lattice:
            for words in lattice[speaker]:
                    transcription_result.append([lattice[speaker][words]["start"],
                                                 lattice[speaker][words]["best_path"],
                                                 lattice[speaker][words].get("speaker", "1"),
                                                 lattice[speaker][words]["word"]])
        transcription_result.sort()

        body = "開始時間,話者,内容"
        speaker = -1

        for lists in transcription_result:
            if (lists[3] != "!NULL" and
                    lists[3] != "!ENTER" and
                    lists[3] != "!EXIT" and
                    lists[3] != "はい" and
                    lists[3] != "はいはい" and
                    lists[3] != "あー" and
                    lists[3] != "あぁ" and
                    # lists[3] != "。" and
                    # lists[3] != "、" and
                    lists[1] is True):

                lists[3] = lists[3].replace("＋", "+")
                # lists[3] = lists[3].replace("-", "―")
                if lists[2] == speaker:
                    body = body[:len(body) - 1] + str(lists[3]) + "\""
                else:
                    body += "\n" + str(lists[0]) + \
                            ",話者:" + str(lists[2]) + \
                            "," + "\"" + str(lists[3]) + "\""
                speaker = lists[2]

        return body

    def file_output(self, data, output_file):
        o = codecs.open(output_file, "w", "utf-8-sig")
        o.write(data)
        o.close()


if __name__ == '__main__':
    num_of_speakers = 2
    num_of_rows = 10

    application = wx.App()
    frame = MainFrame()
    frame.Show()
    application.MainLoop()
