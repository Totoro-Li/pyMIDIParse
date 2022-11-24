import cv2

if __name__ == '__main__':
    print(cv2.__version__)
    # load image
    img = cv2.imread('../img_sample/screenshot.jpg')
    # detect rectangle
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(gray, 75, 200)
    # find contours
    (cnts, _) = cv2.findContours(edged.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    # sort contours
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]
    screenCnt = None
    # loop over contours
    for c in cnts:
        # approximate contour
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        # if contour has 4 vertices, then it is a rectangle
        if len(approx) == 4:
            screenCnt = approx
            break
    # draw rectangle
    cv2.drawContours(img, [screenCnt], -1, (0, 255, 0), 2)
    # show image
    cv2.imshow('image', img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

    # save image
    cv2.imwrite('../img_sample/processed.jpg', img)
