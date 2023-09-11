# Run this script to test the scorecard rendering. It will pull data from assets/req-game_3-save_m.xml.


import re, os, glob, logging
from lxml import etree
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Tuple

log = logging.getLogger('scorecard')
log.setLevel(logging.INFO)

package_dir = Path(os.path.relpath(__file__)).parent


# Seek past the xml declaration since we're specifying encoding, cause lxml doesn't like it when we do that.
def seekXml(path):
    with open(path, 'r', encoding='shift_jisx0213') as f:
        if '<?xml' in f.readline():
            return etree.parse(f)
        else:
            f.seek(0)
            return etree.parse(f)

mdb = seekXml(str(package_dir / 'assets/music-info-b.xml'))

img_save_dir = package_dir / 'static'

class ScoreCard:
    """
    Requires an xml request of game_3/save_m.
    Optional hiscore (add an 'old_score' element in the response) will display score difference on card.
    Museca has an "Upload image" button on the results screen that sets the eaappli/is_image_store flag in the save_m request.
    Check that flag to determine if it was pressed. The game doesn't actually take a screenshot.
    The feature is activated by setting game_3/eaappli/relation to 1 in the game_3.load response. (It was never utilized on real eamuse.)

    Usage:
    from scorecard import ScoreCard
    scorecard = ScoreCard(xml_bytes)
    scorecard.generate()
    Returns the image bytes or the file path, if you choose to save the image instead. See return of self.create_image.
    Also returns the info dict

    """
    def __init__(self, save_m):
        try:
            self.call = etree.parse(BytesIO(save_m)).getroot()
        except TypeError:
            self.call = etree.parse(save_m).getroot()

    def generate(self) -> Tuple[Path, dict]:
        info = self.extract_info(self.call)
        outfile = self.create_image(info)
        return outfile, info

    def extract_info(self, call):
        game_3 = call.find('game_3')
        info = {}
        info['model'] = call.get('model')
        info['music_id'] = game_3.find('music_id').text
        info['music_type'] = game_3.find('music_type').text
        info['new_score'] = game_3.find('score').text
        info['clear_type'] = game_3.find('clear_type').text
        info['score_grade'] = game_3.find('score_grade').text
        info['max_combo'] = game_3.find('max_chain').text
        info['critical'] = game_3.find('critical').text
        info['near'] = game_3.find('near').text
        info['error'] = game_3.find('error').text
        info['etc'] = game_3.find('etc').text
        info['player_name'] = game_3.find('eaappli').find('player_name').text
        info['track_no'] = game_3.find('eaappli').find('track_no').text
        etc = re.split(':|,|-|>|[G]|\(|\)', info.get('etc'))
        info['grafica_1'] = etc[1]
        info['grafica_2'] = etc[2]
        info['grafica_3'] = etc[3]
        info['grafica_1_medel'] = etc[7]
        info['grafica_2_medel'] = etc[10]
        info['grafica_3_medel'] = etc[13]
        info['curator_rank'] = etc[19]
        info['curve'] = etc[23]
        info['object_placement'] = etc[25]
        if 'mission' in etc:
            info['mission_grafica'] = etc[28]
            info['mission_level'] = etc[29]
            info['mission_percentage'] = etc[30]

        music = mdb.find(f'music[@id="{info["music_id"]}"]')
        if music is None :
            raise Exception("This song isn't in the musicdb.")
        info['title'] = music.find('info').find('title_name').text
        info['artist'] = music.find('info').find('artist_name').text
        diffmap = {'0': 'novice', '1': 'advanced', '2': 'exhaust'}
        diff = diffmap.get(info['music_type'])
        info['difficulty'] = music.find('difficulty').find(diff).find('difnum').text
        try:
            info['old_score'] = game_3.find('old_score').text
        except:
            #If the client didn't add an old_score element, the score difference won't be displayed on the generated image.
            pass

        return info

    def create_image(self, info):
        try:
            info['title']
        except:
            log.error("This song isn't in the musicdb.")
            raise Exception("This song isn't in the musicdb.")

        base = Image.open(package_dir / 'assets/misc/bg.png')
        draw = ImageDraw.Draw(base)
        # Gotta use str(package_dir) because ImageFont doesn't like the path object.
        namefont = ImageFont.truetype(str(package_dir / "assets/font/museca.ttf"), size=50)
        scorefont = ImageFont.truetype(str(package_dir / "assets/font/museca.ttf"), size=37)
        subscorefont = ImageFont.truetype(str(package_dir / "assets/font/museca.ttf"), size=22)
        dtfont = ImageFont.truetype(str(package_dir / "assets/font/dfgothw2.ttc"), size=15, index=2)
        title_font = ImageFont.truetype(str(package_dir / "assets/font/msgothic.ttc"), size=15, index=1)
        title_font_s = ImageFont.truetype(str(package_dir / "assets/font/msgothic.ttc"), size=14, index=1)
        artist_font = ImageFont.truetype(str(package_dir / "assets/font/msgothic.ttc"), size=13, index=1)
        record_font = ImageFont.truetype(str(package_dir / "assets/font/museca.ttf"), size=18)
        record_font_shadow = ImageFont.truetype(str(package_dir / "assets/font/museca.ttf"), size=19)
        record_font_2 = ImageFont.truetype(str(package_dir / "assets/font/museca.ttf"), size=15)

        # ----- Name text -----
        draw.text((161, 45), info['player_name'], (0, 0, 0), font=namefont)

        # ----- Time text -----
        now = datetime.now(timezone.utc).strftime("%Y/%m/%d - %I:%M%p UTC")
        draw.text((161, 100), now, (133, 133, 133), font=dtfont)

        # ----- Curator Rank -----
        with Image.open(package_dir / 'assets/rank/rank_{}.png'.format(int(info['curator_rank']))) as rankimg:
            base.paste(rankimg, (69, 26), mask=rankimg)

        # ----- Jacket -----
        try:
            base.paste(Image.open(
                package_dir / 'assets/jackets/jk_01_{:0>4s}_{}_b.png'.format(info['music_id'], int(info['music_type']) + 1)),
                (471, 124))
            if int(info['music_id']) > 226:
                with Image.open(package_dir / 'assets/misc/mplus.png') as mplus:
                    base.paste(mplus, (425, 127), mask=mplus)
        except FileNotFoundError:
            try:
                base.paste(Image.open(package_dir / 'assets/jackets/jk_01_{:0>4s}_1_b.png'.format(info['music_id'])), (471, 124))
                if int(info['music_id']) > 226:
                    with Image.open(package_dir / 'assets/misc/mplus.png') as mplus:
                        base.paste(mplus, (425, 127), mask=mplus)
            except FileNotFoundError:
                try:
                    base.paste(Image.open(package_dir / 'assets/jackets/jk_01_0000_0_b.png'), (471, 124))
                    if int(info['music_id']) > 226:
                        log.error("Jacket(s) don't exist, using default jacket.")
                        with Image.open(package_dir / 'assets/misc/mplus.png') as mplus:
                            base.paste(mplus, (425, 127), mask=mplus)
                except FileNotFoundError:
                    log.error("Jacket(s) don't exist, did you fuck something up?")

        # ----- Title text -----
        title = self.fixBrokenChars(info['title'])
        titleW, titleH = draw.textsize(title, font=title_font)
        if titleW > 247:
            titleW, titleH = draw.textsize(title, font=title_font_s)
            titlecanvas = Image.new('RGBA', (titleW, titleH), color=(255, 255, 255, 0))
            titledraw = ImageDraw.Draw(titlecanvas)
            titledraw.text((0, 0), title, (30, 30, 30), font=title_font_s)
            if titlecanvas.size[0] > 247:  # If the smaller font size still doesn't fit, resize the text image to fit.
                titlecanvas = titlecanvas.resize((247, titleH), resample=Image.LANCZOS)
            base.paste(titlecanvas, (694 - titlecanvas.size[0], 359), mask=titlecanvas)
        else:
            draw.text((694 - draw.textsize(title, font=title_font)[0], 359), title, (30, 30, 30),
                      font=title_font)

        # ------ Artist text ------
        artist = self.fixBrokenChars(info['artist'])
        artistW, artistH = draw.textsize(artist, font=artist_font)
        if artistW > 247:
            artistcanvas = Image.new('RGBA', (artistW, artistH), color=(255, 255, 255, 0))
            artistdraw = ImageDraw.Draw(artistcanvas)
            artistdraw.text((0, 0), artist, (120, 120, 120), font=artist_font)
            artistcanvas = artistcanvas.resize((247, artistH), resample=Image.LANCZOS)
            base.paste(artistcanvas, (694 - artistcanvas.size[0], 382), mask=artistcanvas)
        else:
            draw.text((694 - draw.textsize(artist, font=artist_font)[0], 382), artist, (120, 120, 120), font=artist_font)

        # ----- Score text -----
        draw.text((694 - draw.textsize(info['new_score'], font=scorefont)[0], 431), info['new_score'], (0, 0, 0),
                  font=scorefont)
        draw.text((693 - draw.textsize(info['new_score'], font=scorefont)[0], 431), info['new_score'], (0, 0, 0),
                  font=scorefont)  # doubled for bold
        draw.text((694 - draw.textsize(info['critical'], font=subscorefont)[0], 496), info['critical'], (0, 0, 0),
                  font=subscorefont)
        draw.text((694 - draw.textsize(info['near'], font=subscorefont)[0], 525), info['near'], (0, 0, 0),
                  font=subscorefont)
        draw.text((694 - draw.textsize(info['error'], font=subscorefont)[0], 554), info['error'], (0, 0, 0),
                  font=subscorefont)
        draw.text((694 - draw.textsize(info['max_combo'], font=subscorefont)[0], 583), info['max_combo'], (0, 0, 0),
                  font=subscorefont)

        # ----- Level -----
        with Image.open(package_dir / 'assets/numbers/lv_{}.png'.format(info['difficulty'])) as levelimg:
            base.paste(levelimg, (609, 41), mask=levelimg)
        with Image.open(package_dir / 'assets/misc/difficulty_{}.png'.format(int(info['music_type']))) as levelicon:
            base.paste(levelicon, (542, 89), mask=levelicon)

        # ----- Grade -----
        with Image.open(package_dir / 'assets/grade/grade_{}.png'.format(info['score_grade'])) as grade:
            base.paste(grade, (467, 682), mask=grade)
        pointer_x_map = {'0': 485, '1': 512, '2': 538, '3': 564, '4': 591, '5': 617, '6': 643, '7': 669, '8': 669}
        if info['score_grade'] == '8':
            with Image.open(package_dir / 'assets/misc/grade_index_2.png') as pointer:
                base.paste(pointer, (pointer_x_map.get(info['score_grade']), 650), mask=pointer)
        else:
            with Image.open(package_dir / 'assets/misc/grade_index_0.png') as pointer:
                base.paste(pointer, (pointer_x_map.get(info['score_grade']), 650), mask=pointer)

        # ----- Track number -----
        with Image.open(package_dir / 'assets/misc/track_{}.png'.format(info['track_no'])) as layer:
            base.paste(layer, (0, 221), mask=layer)

        # ----- GRAFICA -----
        if info['grafica_1'] != '0':
            base.paste(Image.open(package_dir / 'assets/grafica/{}.png'.format(info['grafica_1'])), (126, 134))
            with Image.open(package_dir / 'assets/medel/medel_{}.png'.format(info['grafica_1_medel'])) as medel:
                base.paste(medel, (186, 320), mask=medel)
            with Image.open(package_dir / 'assets/misc/frame_1.png') as frame:
                base.paste(frame, (126, 134), mask=frame)
        if info['grafica_2'] != '0':
            base.paste(Image.open(package_dir / 'assets/grafica/{}.png'.format(info['grafica_2'])), (126, 402))
            with Image.open(package_dir / 'assets/medel/medel_{}.png'.format(info['grafica_2_medel'])) as medel:
                base.paste(medel, (186, 588), mask=medel)
            with Image.open(package_dir / 'assets/misc/frame_2.png') as frame:
                base.paste(frame, (126, 402), mask=frame)
        if info['grafica_3'] != '0':
            base.paste(Image.open(package_dir / 'assets/grafica/{}.png'.format(info['grafica_3'])), (126, 668))
            with Image.open(package_dir / 'assets/medel/medel_{}.png'.format(info['grafica_3_medel'])) as medel:
                base.paste(medel, (186, 854), mask=medel)
            with Image.open(package_dir / 'assets/misc/frame_3.png') as frame:
                base.paste(frame, (126, 668), mask=frame)

        # ----- Connect All -----
        if info['clear_type'] == '4':
            base.paste(Image.open(package_dir / 'assets/misc/ca_icon_big.png'), (475, 501))

        # ----- Score difference -----
        if 'old_score' in info.keys():
            old_score, new_score = int(info['old_score']), int(info['new_score'])
            # print(old_score, new_score)
            if new_score > old_score:
                with Image.open(package_dir / 'assets/misc/new_record_text.png') as new_record:
                    base.paste(new_record, (493, 471), mask=new_record)
                diff = new_score - old_score
                diff = '+' + str(diff)
                draw.text((693 - draw.textsize(diff, font=record_font_shadow)[0], 467), diff, (84, 84, 84, 33),
                          font=record_font_shadow)
                draw.text((694 - draw.textsize(diff, font=record_font)[0], 467), diff, (84, 84, 84, 33),
                          font=record_font)
                draw.text((693 - draw.textsize(diff, font=record_font)[0], 467), diff, (255, 255, 255),
                          font=record_font)
                draw.text((692 - draw.textsize(diff, font=record_font)[0], 467), diff, (255, 255, 255),
                          font=record_font)
                draw.text((692 - draw.textsize(diff, font=record_font)[0], 467), diff, (255, 255, 255),
                          font=record_font)
            elif new_score <= old_score:
                diff = str(new_score - old_score)
                with Image.open(package_dir / 'assets/misc/minus_record_bg.png') as minus_record:
                    base.paste(minus_record, (493, 470), mask=minus_record)
                draw.text((692 - draw.textsize(diff, font=record_font_2)[0], 471), diff, (0, 0, 0), font=record_font_2)

        # ----- Object Placement -----
        if info['object_placement'] == '1':
            with Image.open(package_dir / 'assets/misc/option_mirror.png') as mirror:
                base.paste(mirror, (472, 411), mask=mirror)
        elif info['object_placement'] == '2':
            with Image.open(package_dir / 'assets/misc/option_random.png') as random:
                base.paste(random, (472, 411), mask=random)
        elif info['object_placement'] == '3':
            with Image.open(package_dir / 'assets/misc/option_sran.png') as sran:
                base.paste(sran, (472, 411), mask=sran)
        if info['curve'] == '1':
            with Image.open(package_dir / 'assets/misc/option_curve_1.png') as curve:
                base.paste(curve, (537, 411), mask=curve)
        elif info['curve'] == '2':
            with Image.open(package_dir / 'assets/misc/option_curve_2.png') as curve:
                base.paste(curve, (537, 411), mask=curve)

        # Two ways you can go from here. Either return the image bytes directly...
        # return base
        # Or save the image and return the filename...
        return self.saveImage(base)

    def saveImage(self, base):
        """
        Save image to img_save_dir using the next available name number.
        I use a cronjob to delete the images every so often. If you want to store them on the server
        indefinitely, you may want to use a database to store the number instead.
        """
        currentImages = glob.glob("{}/*.png".format(img_save_dir))
        numList = [0]
        for img in currentImages:
            i = os.path.splitext(img)[0]
            try:
                num = re.findall('[0-9]+$', i)[0]
                numList.append(int(num))
            except IndexError:
                pass
        numList = sorted(numList)
        newNum = str(numList[-1] + 1)
        saveName = img_save_dir / f'{newNum}.png'
        log.info("Saving imgscore %s", saveName)
        base.save(saveName)
        if __name__ == '__main__':
            base.show()
        return saveName

    def fixBrokenChars(self, name):  # thanks mon
        # a bunch of chars get mapped oddly - bemani specific fuckery
        replacements = [
            [u'\u203E', u'~'],
            [u'\u301C', u'～'],
            [u'\u49FA', u'ê'],
            [u'\u5F5C', u'ū'],
            [u'\u66E6', u'à'],
            [u'\u66E9', u'è'],
            [u'\u8E94', u'🐾'],
            [u'\u9A2B', u'á'],
            [u'\u9A69', u'Ø'],
            [u'\u9A6B', u'ā'],
            [u'\u9A6A', u'ō'],
            [u'\u9AAD', u'ü'],
            [u'\u9B2F', u'ī'],
            [u'\u9EF7', u'ē'],
            [u'\u9F63', u'Ú'],
            [u'\u9F67', u'Ä'],
            [u'\u973B', u'♠'],
            [u'\u9F6A', u'♣'],
            [u'\u9448', u'♦'],
            [u'\u9F72', u'♥'],
            [u'\u9F76', u'♡'],
            [u'\u9F77', u'é'],
            [u'\u8E59', u'ℱ'],
            [u'\u96CB', u'Ǜ'],
            [u'\u9B44', u'♃'],
            [u'\u9B25', u'Ã'],
            [u'\u9B06', u'Ý'],
            [u'\u968D', u'Ü'],
            [u'\u9B2E', u'¡'],
            [u'\u99B9', u'©'],
            [u'\u99BF', u'♠'],
        ]
        for rep in replacements:
            name = name.replace(rep[0], rep[1])
        return name


if __name__ == '__main__':
    tree = etree.parse('assets/req-game_3-save_m.xml')
    data = etree.tostring(tree)
    scorecard = ScoreCard(data)
    scorecard.generate()
