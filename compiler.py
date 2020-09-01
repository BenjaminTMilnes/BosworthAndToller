

def getPageText(pageNumber = ""):

    pageLines = []

    with open("data.txt", "r") as fileObject:
        lines = fileObject.readlines()

        isOnPage = False

        for line in lines:
            if line.startswith("<PAGE NUM=\"{0}\"".format(pageNumber)):
                isOnPage = True
            elif line.startswith("<PAGE NUM="):
                isOnPage = False 

            if isOnPage:
                pageLines.append(line)

    return "\n".join(pageLines)
    

if __name__ == "__main__":
    print(getPageText("b0004"))


