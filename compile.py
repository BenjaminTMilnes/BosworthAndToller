import os 
import glob 
import json 
import re 
from tauparsing.core import * 
import logging 
from lxml import etree 

logging.basicConfig(level=logging.DEBUG)

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
        self.conjugations = {}
        self.partOfSpeech = ""
        self.modernEnglishMeanings = []
        self.latinMeanings = []
        self.examples = []

    def toDictionary(self):
        return {
            "heading": self.heading,
            "alternativeSpellings": self.alternativeSpellings,
            "pluralForms": self.pluralForms,
            "conjugations": self.conjugations,
            "partOfSpeech": self.partOfSpeech,
            "modernEnglishMeanings": self.modernEnglishMeanings,
            "latinMeanings": self.latinMeanings,
            "examples": [example.toDictionary() for example in self.examples],
            "text": self.text 
        }

class Example(object):
    def __init__(self):
        self.text = ""
        self.oldEnglish = ""
        self.modernEnglish = ""
        self.latin = ""
        self.references = []

    def toDictionary(self):
        return {
            "oldEnglish":self.oldEnglish,
            "modernEnglish": self.modernEnglish,
            "latin": self.latin,
            "references": self.references,
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

referenceAbbreviations = {}

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

class BosworthAndTollerParser(Parser):

    def _getEntry(self, inputText, marker):
        heading = self._getBoldSection(inputText, marker)

        if heading == None:
            return None 

        heading = heading[1] 
        heading = replaceEntities(heading)
        heading = removeTrailingPunctuation(heading)

        entry = Entry()
        entry.heading = heading 

        alternativeSpellings, pluralForms = self._getAlternativeSpellingsAndPluralForms(inputText, marker)

        entry.alternativeSpellings = alternativeSpellings 
        entry.pluralForms = pluralForms 

        partOfSpeech, conjugations, modernEnglishMeanings, latinMeanings = self._getPartOfSpeechAndMeanings(inputText, marker)

        entry.conjugations = conjugations 
        entry.partOfSpeech = partOfSpeech 
        entry.modernEnglishMeanings = modernEnglishMeanings 
        entry.latinMeanings = latinMeanings 

        examples = self._getExamples(inputText, marker)

        entry.examples = examples 

        return entry 

    def _getBoldSection(self, inputText, marker):

        m = marker 

        if cut(inputText, m.p, 3) == "<B>":
            m.p += 3
        else:
            return None 

        t = ""

        while m.p < len(inputText):
            if m.p < len(inputText) - 4 and cut(inputText, m.p, 4) == "</B>":
                m.p += 4
                break 
            else:
                t += inputText[m.p]
                m.p += 1 

        return ("bold", t)

    def _getItalicSection(self, inputText, marker):
        
        m = marker 

        if cut(inputText, m.p, 3) == "<I>":
            m.p += 3
        else:
            return None 

        t = ""

        while m.p < len(inputText):
            if m.p < len(inputText) - 4 and cut(inputText, m.p, 4) == "</I>":
                m.p += 4
                break 
            else:
                t += inputText[m.p]
                m.p += 1 

        return ("italic", t)

    def _getTextSection(self, inputText, marker):

        m = marker 

        t = ""

        while m.p < len(inputText):
            if m.p < len(inputText) - 3 and cut(inputText, m.p, 3) in ["<B>", "<I>"]:
                break 
            else:
                t += inputText[m.p]
                m.p += 1 

        return ("text", t)

    def _getAlternativeSpellingsAndPluralForms(self, inputText, marker):

        m = marker 

        i = m.p 
        j = inputText.find("<I>")
        t = inputText[i:j].strip()
        t = replaceEntities(t)

        alternativeSpellingsAndPluralForms = re.split(",|;", t)
        alternativeSpellingsAndPluralForms = [a.strip() for a in alternativeSpellingsAndPluralForms if a.strip() != ""]
        alternativeSpellings = [a for a in alternativeSpellingsAndPluralForms if a not in ["an", "e", "es"]]
        pluralForms = [a for a in alternativeSpellingsAndPluralForms if a in ["an", "e", "es"]]

        m.p = j 

        return (alternativeSpellings, pluralForms)

    def _getPartOfSpeechAndMeanings(self, inputText, marker):
        
        logging.debug("Getting part of speech, conjugations, and meanings at '{}'.".format(inputText[marker.p:marker.p+20]))

        partOfSpeech = ""
        conjugations = {}
        modernEnglishMeanings = []
        latinMeanings = [] 

        m1 = marker 
        i = m1.p 
        j = inputText.find(":--")

        if j >= 0:
            t = inputText[i:j]

            sections = []
            m2 = Marker()

            while m2.p < len(t):
                
                s = self._getBoldSection(t, m2)

                if s != None:
                    sections.append(s)
                    continue 
                
                s = self._getItalicSection(t, m2)

                if s != None:
                    sections.append(s)
                    continue 

                s = self._getTextSection(t, m2)

                if s != None:
                    sections.append(s)
                    continue 

                break 

            if len(sections) > 0:
                if sections[0][0] == "italic" and sections[0][1] == "p.":
                    partOfSpeech = "verb"
                    conjugations["p"] = sections[1][1]

                    if len(sections) > 2 and sections[2][0] == "italic" and sections[2][1] == "pp.":
                        conjugations["pp"] = sections[3][1]

                    if len(sections) > 4:
                        meaning = sections[4][1]
                        modernEnglishMeanings.append(meaning)

                elif sections[0][0] == "italic":

                    for a, b in partsOfSpeech.items():
                        if sections[0][1].startswith(a):
                            partOfSpeech = b 
                            meaning = sections[0][1][len(a):]
                            modernEnglishMeanings.append(meaning)

                n = len(sections)
                lastSection = sections[n-1]                            

                if lastSection[0] == "text":
                    meaning = lastSection[1]
                    latinMeanings.append(meaning)

            m1.p = j + 3 

        conjugations = {a: removeTrailingPunctuation(b.strip()).strip() for a, b in conjugations.items()}
        modernEnglishMeanings = [removeTrailingPunctuation(m.strip()).lower() for m in modernEnglishMeanings]
        latinMeanings = [removeTrailingPunctuation(m.strip()).lower() for m in latinMeanings]

        return (partOfSpeech, conjugations, modernEnglishMeanings, latinMeanings)

    def _getExamples(self, inputText, marker):
        m = marker 

        examples = []

        n = 0

        while m.p < len(inputText):
            if n > 0:
                if inputText[m.p] == ".":
                    m.p += 1 
                else:
                    break 

            example = self._getExample(inputText, m)

            if example != None:
                examples.append(example)
                n += 1 
            else:
                break 

        return examples 

    def _getExample(self, inputText, marker):

        oldEnglish = ""
        meaning = ""
        references = []

        s1 = self._getTextSection(inputText, marker)

        if s1 == None:
            return None 
        else:
            oldEnglish = s1[1]

        s2 = self._getItalicSection(inputText, marker)

        if s2 == None:
            return None 
        else:
            meaning = s2[1]

        references = self._getReferenceList(inputText, marker)

        example = Example()

        example.oldEnglish = replaceEntities(oldEnglish).strip() 
        example.latin = removeTrailingPunctuation(meaning.strip()).strip() 
        example.references = references 

        return example 

    def _getReferenceList(self, inputText, marker):
        m = marker 

        references = []

        n = 0

        while m.p < len(inputText):
            if n > 0:
                self._getWhiteSpace(inputText, m)
                if inputText[m.p] == ";":
                    m.p += 1
                else:
                    break 

            self._getWhiteSpace(inputText, m)
            reference = self._getReference(inputText, m)

            if reference != None:
                references.append(reference)
                n += 1
            else:
                break 

        if len(references) == 0:
            return None 

        return references 

    def _getReference(self, inputText, marker):
        m = marker 

        source = ""
        pageNumbers = []
        abbreviations = sorted([a for a, b in referenceAbbreviations.items()], key = lambda a: len(a), reverse=True)

        for a in abbreviations:
            if inputText[m.p:].startswith(a):
                source = a 
                m.p += len(a)
                break 

        pageNumbers = self._getPageNumberList(inputText, m)

        if source == "" or pageNumbers == None:
            return None 

        return (source, pageNumbers)
        

    def _getPageNumberList(self, inputText, marker):

        m = marker 

        pageNumbers = []

        n = 0

        while m.p < len(inputText):
            if n > 0:
                self._getWhiteSpace(inputText, m)
                if inputText[m.p] == ",":
                    m.p += 1
                else:
                    break 

            self._getWhiteSpace(inputText, m)
            pageNumber = self._getInteger(inputText, m)

            if pageNumber != None:
                pageNumbers.append(pageNumber)
                n += 1
            else:
                break 

        if len(pageNumbers) == 0:
            return None 

        return pageNumbers 

    def _getInteger(self, inputText, marker):

        m = marker 

        t = ""

        for c in inputText[m.p:]:
            if c in "0123456789":
                t += c
                m.p += 1
            else:
                break 

        if t == "":
            return None 

        return t 


def compilePages():

    if not os.path.exists("data"):
        os.mkdir("data")

    fps = glob.glob("data/*.json")

    for fp in fps:
        os.remove(fp)


    with open("bosworth_and_toller.txt", "r") as fo:
        lines = fo.readlines()
        lines = [line.strip() for line in lines if line.strip() != ""]
            
        parser = BosworthAndTollerParser()

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
                entry = parser._getEntry(line, Marker())
                entry.text = line 
                
                page.entries.append(entry)

        if page != None:
            pages.append(page)

        for page in pages[9:10]:
            print(page.number)
            for entry in page.entries:
                print("{} | {} | {}".format(entry.heading, entry.partOfSpeech, entry.modernEnglishMeanings))

        print(len(pages))

        for page in pages[9:13]:
            with open(os.path.join("data", "{}.json".format(page.number)), "w", encoding="utf-8") as fo2:
                json.dump(page.toDictionary(), fo2, indent=4)

def compileAbbreviations():
    abbreviations = []

    tree = etree.parse("bosworth_and_toller_abbreviations.xml")

    sources = tree.xpath("/document/source")

    for source in sources:
        heading = source.xpath("./heading")[0].text
        spellings = [spelling.text for spelling in source.xpath("./spellout")]
        text = source.xpath("./body")[0].text

        text = text.replace("\n", " ")
        text = text.strip()

        abbreviation = {
            "heading": heading,
            "spellings": spellings,
            "text": text 
        }

        abbreviations.append(abbreviation)

    with open("bosworth_and_toller_abbreviations.json", "w") as fo:
        json.dump(abbreviations, fo, indent=4)

    for abbreviation in abbreviations:
        for spelling in abbreviation["spellings"]:
            referenceAbbreviations[spelling] = abbreviation 

if __name__ == "__main__":

    compileAbbreviations()
    compilePages()


