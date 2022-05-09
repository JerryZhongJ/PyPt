import argparse
import json
from PyPt.CSPTA.Analysis import Analysis as csAnalysis
from PyPt.PTA.Analysis import Analysis

from PyPt.ModuleManager import ModuleManager, ModuleNotFoundException


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("filepath", 
        nargs="?",
        help="Entry point is a python script. Just like how you run program directly using \"python filename.py\"."
    )
    argparser.add_argument("-m", "--module",
        help="Entry point is a library module. Just like how you run program using \"python -m \"."
    )
    argparser.add_argument("-cs", "--context-sensitive",
        action="store_true",
        default=False,
        help="Enable context sensitive. It may cost longer time."
    )
    argparser.add_argument("-o", "--output",
        required=True,
        help="The file path where output callgraph will be stored. The output format will json."
    )
    argparser.add_argument("-nd", "--no-dependency",
        action="store_true",
        default=False,
        help="""If in script mode, only modules under the same directory as the entry point will be included.\
                If in module mode, only modules under current directory will be included."""
    )
    args = argparser.parse_args()
    if(args.filepath and args.module):
        print("Error: Please provide one entry point at a time.")
        exit()
    if(not args.filepath and not args.module):
        print("Error: No entry point is provided.")
        exit()

    fp = open(args.output, "w")

    mm = ModuleManager(verbose=True)
    try:
        if(args.filepath):
            mm.start(filepath=args.filepath, dependency=not args.no_dependency)
        if(args.module):
            mm.start(module=args.module)
    except ModuleNotFoundException as e:
        print(f"Error: {e}")
        exit()
    except ValueError as e:
        print(f"Error: {e}")
        exit()

    print("IR generation is done, start Point-to Analysis...                ")
    if(args.context_sensitive):
        analysis = csAnalysis(verbose=True)
    else:
        analysis = Analysis(verbose=True)

    analysis.analyze(mm.getCodeBlock("__main__"))
    print("Point-to Analysis is done, start writing to file                ")
    
    json.dump(analysis.callgraph.export(), fp=fp)

    print("All done.")
    fp.close()
    