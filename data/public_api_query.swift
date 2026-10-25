import FoundationModels
import Foundation

@main struct Q {
    static func main() async {
        let m = SystemLanguageModel.default
        print("availability:", m.availability)
        print("variant (default):", m.variant.displayName)
        let tag = SystemLanguageModel(useCase: .contentTagging)
        print("variant (contentTagging):", tag.variant.displayName)
        let perm = SystemLanguageModel(useCase: .general, guardrails: .permissiveContentTransformations)
        print("variant (permissive guardrails):", perm.variant.displayName)
        print("known variants: core3 =", SystemLanguageModel.Variant.core3.displayName, "| coreAdvanced3 =", SystemLanguageModel.Variant.coreAdvanced3.displayName)
        print("variant == core3:", m.variant == .core3, "| == coreAdvanced3:", m.variant == .coreAdvanced3)
        print("contextSize:", m.contextSize)
        let caps = m.capabilities
        print("capabilities: vision=\(caps.contains(.vision)) guidedGeneration=\(caps.contains(.guidedGeneration)) reasoning=\(caps.contains(.reasoning)) toolCalling=\(caps.contains(.toolCalling))")
        let langs = m.supportedLanguages.map { $0.maximalIdentifier }.sorted()
        print("supportedLanguages (\(langs.count)):", langs.joined(separator: ", "))
        for s in ["Say hi.", "The quick brown fox jumps over the lazy dog."] {
            if let n = try? await m.tokenCount(for: s) { print("tokenCount(\"\(s)\") =", n) }
        }
        if let n = try? await m.tokenCount(for: Instructions("Be brief.")) { print("tokenCount(Instructions 'Be brief.') =", n) }
        print("PCC model availability (no request sent):", PrivateCloudComputeLanguageModel().availability)
    }
}
