import FoundationModels
import Foundation
@main struct L {
    static func main() async {
        let m = SystemLanguageModel.default
        let tests = ["en-US","fr-FR","fr-CH","de-AT","es-MX","pt-BR","it-IT","nl-BE","ja-JP","ko-KR","zh-Hans-CN","zh-Hant-TW","yue-HK","ar-SA","he-IL","hi-IN","ru-RU","uk-UA","pl-PL","cs-CZ","el-GR","th-TH","id-ID","ms-MY","fa-IR","tr-TR","vi-VN","da-DK","sv-SE","nb-NO","fi-FI","ro-RO","hu-HU","bn-BD","sw-KE"]
        var yes: [String] = [], no: [String] = []
        for t in tests { (m.supportsLocale(Locale(identifier: t)) ? { yes.append(t) } : { no.append(t) })() }
        print("supportsLocale TRUE :", yes.joined(separator: " "))
        print("supportsLocale FALSE:", no.joined(separator: " "))
    }
}
