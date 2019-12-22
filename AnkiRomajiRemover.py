# -*- coding:utf-8 -*-
import argparse
import EDictTools
import json
import romkan
import sys
import urllib.request
import UnicodeHelpers


argParser = argparse.ArgumentParser(
    description="""Automatically turn Romaji into Hiragana in an Anki deck.

This is for if you get bothered by Romaji's inaccuracy, or in my opinion, its somewhat misleading format.

This tool takes the name of a deck and the name of the field with Romaji, and converts it into Hiragana.

It preserves most anything which isn't romaji, so if you have e.g. "setsumei(suru)" it will convert it to "せつめい(する)".
"-" and "’" will be removed, however. This is because the romkan converter can get confused by these.
It doesn't hurt to run the script again on a deck which has already been wholly or partially converted.
Katakana will be output if a "written field" is provided to hint the script that it should use katakana.""")
argParser.add_argument('DeckName', type=str,
                       help='The name of the deck to modify. Add "quotes" if the name has spaces, e.g. "My Deck"')
argParser.add_argument('RomajiFieldName', type=str,
                       help='The name of the field which has Romaji you want to convert, e.g. "Front"')
argParser.add_argument('--written-field-name', type=str, dest='WrittenFieldName',
                       help='The name of the field which has what would actually be written in '
                       'realistic text (for example, kanji). This can be provided in order to '
                       'hint the converter that it should output katakana instead of hiragana, '
                       'if the word would normally be written as katakana')
argParser.add_argument('--soft-edit', action='store_const', const=True, default=False, dest='debugSoftEdit',
                       help='Do not make changes to the deck. Output all changes that would be made. '
                       'I recommend running the script with this option first, then look over the results '
                       'and confirm whether they are satisfactory.')
argParser.add_argument('--verbose', action='store_const', const=True, default=False, dest='debugVerbose',
                       help='Output more details about the conversion')
argParser.add_argument('--only-warnings', action='store_const', const=True, default=False, dest='debugOnlyWarnings',
                       help='Only output warnings and errors. It is recommended to do this in conjuction '
                       'with --soft-edit to spot problems before running the script')

def formatAnkiConnectRequest(action, **params):
    return {'action': action, 'params': params, 'version': 6}

def invokeAnkiConnect(action, **params):
    requestJson = json.dumps(formatAnkiConnectRequest(action, **params)).encode('utf-8')
    response = json.load(urllib.request.urlopen(urllib.request.Request('http://localhost:8765', requestJson)))
    if len(response) != 2:
        raise Exception('response has an unexpected number of fields')
    if 'error' not in response:
        raise Exception('response is missing required error field')
    if 'result' not in response:
        raise Exception('response is missing required result field')
    if response['error'] is not None:
        raise Exception(response['error'])
    return response['result']

def getNotes(deckName):
    cardsInDeck = invokeAnkiConnect('findCards', query='"deck:{}"'.format(deckName))
    if not cardsInDeck:
        print("No cards in deck '{}'".format(deckName))
        return []
    print("{} cards in deck '{}'".format(len(cardsInDeck), deckName))
    return invokeAnkiConnect('cardsToNotes', cards = cardsInDeck)

def sanitizeTextForConversion(fieldValue):
    # These confuse romkan, and aren't usually a part of the language anyhow
    return fieldValue.replace('-', '').replace('’', '')

def convertNotes(deckName, fieldToConvert, conversionHintField=None,
                 shouldEdit=True):
    notes = getNotes(deckName)
    notesInfo = invokeAnkiConnect('notesInfo', notes = notes)
    for currentNote in notesInfo:
        hasWarnings = False
        textToConvert = sanitizeTextForConversion(currentNote['fields'][fieldToConvert]['value'])
        
        if not textToConvert:
            hasWarnings = True
            print("Error: Empty '{}' found in the following note, which may be malformed:".format(fieldToConvert))
            print(currentNote)
            print("You need to hand-edit this note in order for it to be converted properly.\n"
                  "Look over those fields carefully to see if something looks wrong.\n"
                  "If you find the problem, resolve it using Anki's Browse feature.")
            print("------------------------------")
            # There's nothing we can do if we don't have a value to convert
            continue
        
        hint = (sanitizeTextForConversion(currentNote['fields'][conversionHintField]['value'])
                if conversionHintField else None)

        convertedText = None

        if hint:
            hintContainsCharacterTypes = set()
            for char in hint:
                if not char.isalnum():
                    # Ignore any punctuation
                    continue
                if UnicodeHelpers.is_katakana(char):
                    hintContainsCharacterTypes.add("katakana")
                if UnicodeHelpers.is_hiragana(char):
                    hintContainsCharacterTypes.add("hiragana")
                if UnicodeHelpers.is_kanji(char):
                    hintContainsCharacterTypes.add("kanji")
                if UnicodeHelpers.is_latin(char):
                    hintContainsCharacterTypes.add("latin")

            if args.debugVerbose:
                print("{} -> {}".format(hint, hintContainsCharacterTypes))

            if hintContainsCharacterTypes.issubset({"latin"}):
                # There are no Japanese characters; it's probably an initialism or acronym, e.g. 'WWW'
                # Convert to katakana
                convertedText = romkan.to_katakana(textToConvert)
            elif "kanji" not in hintContainsCharacterTypes:
                # The hint is already readable; just use it. This fixes problems where romkan won't
                # convert continuations properly: from input "booringu" the converter outputs
                # ボオリング instead of ボーリング. This also fixes some problems where romaji is
                # erroneous. It doesn't fix cases where there are Kanji and erroneous romaji
                convertedText = hint
                
        # It's not katakana, or we don't have a hint. Use hiragana
        if not convertedText:
            convertedText = romkan.to_hiragana(textToConvert)

        # No conversion
        if not convertedText:
            hasWarnings = True
            print("ERROR: No conversion for text '{}'".format(textToConvert))
            continue

        suspiciousConversion = False
        for char in convertedText:
            if UnicodeHelpers.is_latin(char):
                print("Warning: conversion did not result in purely Japanese output:\n\t{}\nThere may be "
                      "a typo in the romaji, or the romaji format is not understood.".format(convertedText))
                suspiciousConversion = True
                break

        if suspiciousConversion:
            if not hint:
                hasWarnings = True
                print("Could not use edict to find reading because written field not provided")
            else:
                print("Falling back to edict for {}".format(hint))
                entries = EDictTools.findEntries(hint)
                if args.debugVerbose:
                    for entry in entries:
                        print(entry)
                if entries:
                    if len(entries) > 1:
                        hasWarnings = True
                        print("Warning: multiple entries found:")
                        for entry in entries:
                            print("\t{}".format(entry))
                        # Pick the first one for now
                        convertedText = entries[0].reading
                        suspiciousConversion = True
                    else:
                        print("Using Edict reading: {}".format(entries[0].reading))
                        convertedText = entries[0].reading
                        suspiciousConversion = False
                else:
                    hasWarnings = True
                    print("No readings found for {}".format(hint))

        if hasWarnings:
            print("Conversion had warnings or errors. Adding romaji to field in case of bad conversion")
            convertedText = convertedText + ' ' + currentNote['fields'][fieldToConvert]['value']

        # When not editing, output results to let the user decide if they are ready for the edit
        if args.debugVerbose or not shouldEdit or hasWarnings:
            if args.debugOnlyWarnings and not hasWarnings:
                pass
            else:
                if hint:
                    print("{} -> {} (hint '{}')"
                          .format(currentNote['fields'][fieldToConvert]['value'].ljust(15), convertedText.ljust(15), hint))
                else:
                    print("'{}' -> '{}'"
                          .format(currentNote['fields'][fieldToConvert]['value'], convertedText))

            if hasWarnings:
                print("------------------------------")
                
        if shouldEdit:
            # Already converted
            if textToConvert == convertedText:
                continue

if __name__ == '__main__':
    print('Anki Romaji Remover: Convert Romaji into Hiragana')

    if len(sys.argv) == 1:
        argParser.print_help()
        exit()
    args = argParser.parse_args()

    shouldEdit = not args.debugSoftEdit
    if shouldEdit:
        answer = input("\nWARNING: This script will modify your Anki deck.\n"
                       "This script's creator is not liable for loss of data!\n"
                       "If you want to preview changes, run with --soft-edit.\n"
                       "\nHave you created a backup of your decks? (yes or no) ")
        shouldEdit = answer.lower() in ['yes', 'y']

    if not shouldEdit and not args.debugSoftEdit:
        print("Please back up your data via Anki->File->Export->Anki Collection Package")
    else:
        convertNotes(args.DeckName, args.RomajiFieldName,
                     conversionHintField=args.WrittenFieldName,
                     shouldEdit=shouldEdit and not args.debugSoftEdit)
