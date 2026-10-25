import AppKit
import CoreImage
func png(_ img: NSImage, _ path: String) {
    guard let t = img.tiffRepresentation, let r = NSBitmapImageRep(data: t), let d = r.representation(using: .png, properties: [:]) else { return }
    try? d.write(to: URL(fileURLWithPath: path))
}
func textImage(_ s: String, _ path: String, size: CGFloat) {
    let attrs: [NSAttributedString.Key: Any] = [.font: NSFont.systemFont(ofSize: size), .foregroundColor: NSColor.black]
    let a = NSAttributedString(string: s, attributes: attrs)
    let sz = a.size(); let img = NSImage(size: NSSize(width: sz.width + 40, height: sz.height + 40))
    img.lockFocus(); NSColor.white.setFill(); NSRect(origin: .zero, size: img.size).fill(); a.draw(at: NSPoint(x: 20, y: 20)); img.unlockFocus()
    png(img, path)
}
let dir = CommandLine.arguments[1]
textImage("Invoice 2026-1042\nTotal due: EUR 1,284.50\nPay by 15 November 2026", dir + "/ocr_en.png", size: 36)
textImage("Facture 2026-1042\nMontant dû : 1 284,50 €\nÀ régler avant le 15 novembre 2026", dir + "/ocr_fr.png", size: 36)
textImage("请款单 2026-1042\n应付金额:1284.50 欧元", dir + "/ocr_zh.png", size: 36)
textImage("Small print: terms apply", dir + "/ocr_small.png", size: 11)
let f = CIFilter(name: "CIQRCodeGenerator")!
f.setValue("https://www.julien.org/qr-test-1042".data(using: .utf8), forKey: "inputMessage")
let ci = f.outputImage!.transformed(by: CGAffineTransform(scaleX: 12, y: 12))
let rep = NSCIImageRep(ciImage: ci); let qi = NSImage(size: rep.size); qi.addRepresentation(rep); png(qi, dir + "/qr.png")
let g = CIFilter(name: "CICode128BarcodeGenerator")!
g.setValue("INV20261042".data(using: .ascii), forKey: "inputMessage")
let ci2 = g.outputImage!.transformed(by: CGAffineTransform(scaleX: 6, y: 80))
let rep2 = NSCIImageRep(ciImage: ci2); let bi = NSImage(size: rep2.size); bi.addRepresentation(rep2); png(bi, dir + "/code128.png")
print("ok")
