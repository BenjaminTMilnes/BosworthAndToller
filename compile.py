import os 
import glob 
import json 
import re 

class Page(object):
    def __init__(self):
        self.text = ""
        self.number = ""
        self.entries = []

    def toDictionary(self):
        return {
            "number": self.number,
            "entries": [entry.toDictionary() for entry in self.entries],
            "text": self.text 
        }

class Entry(object):
    def __init__(self):
        self.text = ""
        self.heading = ""
        self.alternativeSpellings = []
        self.pluralForms = []
        self.partOfSpeech = ""
        self.meaning = ""
        self.examples = []

    def toDictionary(self):
        return {
            "heading": self.heading,
            "alternativeSpellings": self.alternativeSpellings,
            "pluralForms": self.pluralForms,
            "partOfSpeech": self.partOfSpeech,
            "meaning": self.meaning,
            "examples": [example.toDictionary() for example in self.examples],
            "text": self.text 
        }

class Example(object):
    def __init__(self):
        self.text = ""
        self.oldEnglish = ""
        self.modernEnglish = ""
        self.latin = ""

    def toDictionary(self):
        return {
            "oldEnglish":self.oldEnglish,
            "modernEnglish": self.modernEnglish,
            "latin": self.latin,
            "text": self.text 
        }

replacements = {
    "&aelig;":"æ",
    "&AElig;": "Æ",
    "&aelig-acute;":"ǽ",
    "&AElig-acute;": "Ǽ",
    "&thorn;":"þ",
    "&THORN;":"Þ",
    "&eth;":"ð",
    "&ETH;":"Ð",
    "&aacute;":"á",
    "&eacute;":"é",
    "&oacute;":"ó",
    "&iacute;":"í",
    "&yacute;":"ý"
}

partsOfSpeech = {
    "adj.": "adjective",
    "adv.": "adverb",
    "interj.":"interjection",
    "prep.":"preposition",
    "part.":"",
    "pp.":"",
    "def. m.":"",
    "m. n.":"",
    "m.":"noun/masculine",
    "f.":"noun/feminine",
    "p.":"",
}

def replaceEntities(text):
    for a, b in replacements.items():
        text = text.replace(a, b)

    return text 

def removeTrailingPunctuation(text):
    if len(text) > 0 and text[-1] in [",",";"]:
        text = text[:-1]

    return text 

def isLatin(text):
    latinOnlyWords = ["erat", "semper", "cum", "enim", "iila", "unquam", "vitia", "exitus"]

    for word in latinOnlyWords:
        if word in text:
            return True 

    return False 

if not os.path.exists("data"):
    os.mkdir("data")

fps = glob.glob("data/*.json")

for fp in fps:
    os.remove(fp)


with open("bosworth_and_toller.txt", "r") as fo:
    lines = fo.readlines()
    lines = [line.strip() for line in lines if line.strip() != ""]

    pages = []
    page = None 

    for line in lines:
        if line.startswith("<PAGE NUM="):
            if page != None:
                pages.append(page)

            page = Page()
            page.number = line[11:16]
            continue 

        if page != None:
            page.text += line 

        if line.startswith("<B>"):
            entry = Entry()
            entry.text = line 

            i = 3
            j = line.find("</B>")

            entry.heading = replaceEntities(line[i:j])

            if entry.heading[-1] in [",", ";"]:
                entry.heading = entry.heading[:-1]

            italicSections = []

            lineAfterHeading = line[j+4:]

            while lineAfterHeading.find("<I>") >= 0:
                k = lineAfterHeading.find("<I>")
                l = lineAfterHeading.find("</I>")
                italicSections.append(lineAfterHeading[k+3:l].strip())
                lineAfterHeading = lineAfterHeading[l+4:]

            a3 = line.find("<I>")

            alternativeSpellingsAndPlurals = replaceEntities(line[j + 4:a3].strip())
            alternativeSpellingsAndPlurals = re.split(",|;", alternativeSpellingsAndPlurals)
            alternativeSpellingsAndPlurals = [a.strip() for a in alternativeSpellingsAndPlurals if a.strip() != ""]
            alternativeSpellings = [a for a in alternativeSpellingsAndPlurals if a not in ["an", "e", "es"]]
            pluralForms =  [a for a in alternativeSpellingsAndPlurals if a in ["an", "e", "es"]]

            entry.alternativeSpellings =alternativeSpellings 
            entry.pluralForms = pluralForms 
            
            a4 = 0

            if len(italicSections) > 0 and italicSections[0] in ["p.", "pp."]:
                entry.partOfSpeech = "verb"

                if len(italicSections) > 0 and italicSections[0] == "p.":
                    a4 += 1

                if len(italicSections) > 1 and italicSections[1] == "pp.":
                    a4 += 1

            if a4 < len(italicSections):
                firstItalicSection = italicSections[a4]

                for a, b in partsOfSpeech.items():
                    if firstItalicSection.startswith(a):
                        entry.partOfSpeech = b 
                        firstItalicSection = firstItalicSection[len(a):]
                        break 

                entry.meaning = firstItalicSection.strip()

            if entry.partOfSpeech in ["adjective", "adverb", "noun/masculine", "noun/feminine", "verb"]:
                entry.meaning = entry.meaning.lower()

            if entry.meaning.endswith(";"):
                entry.meaning = entry.meaning[:-1]

            a5 = line.find(":--")

            if a5 >= 0:
                afterDoubleDash = line[a5 + 3:]

                a6 = afterDoubleDash.find("<I>")
                a7 = afterDoubleDash.find("</I>")

                if a6 >= 0 and a7 >= 0:
                    example = Example()
                    example.text = afterDoubleDash[:a7+4].strip()
                    example.oldEnglish = replaceEntities(afterDoubleDash[:a6].strip())

                    meaning =  removeTrailingPunctuation(afterDoubleDash[a6+3:a7].strip())

                    if isLatin(meaning):
                        example.latin = meaning 
                    else:
                        example.modernEnglish = meaning 

                    entry.examples.append(example)

            page.entries.append(entry)


    if page != None:
        pages.append(page)

    for page in pages[9:10]:
        print(page.number)
        for entry in page.entries:
            print("{} | {} | {}".format(entry.heading, entry.partOfSpeech, entry.meaning))

    print(len(pages))

    for page in pages[9:13]:
        with open(os.path.join("data", "{}.json".format(page.number)), "w", encoding="utf-8") as fo2:
            json.dump(page.toDictionary(), fo2, indent=4)


