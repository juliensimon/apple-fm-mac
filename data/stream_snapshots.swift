import FoundationModels
import Foundation

@main struct S {
    static func main() async {
        let args = Array(CommandLine.arguments.dropFirst())
        guard args.count >= 4, let maxTok = Int(args[1]) else { print("usage: stream <label> <maxTokens> <greedy|temp:T> <prompt...>"); return }
        let label = args[0]
        let mode = args[2]
        let prompt = args.dropFirst(3).joined(separator: " ")
        let session = LanguageModelSession()
        var opts = GenerationOptions()
        if mode == "greedy" { opts.samplingMode = .greedy } else if mode.hasPrefix("temp:"), let T = Double(mode.dropFirst(5)) { opts.samplingMode = .random(top: 100, seed: 7); opts.temperature = T }
        opts.maximumResponseTokens = maxTok
        let t0 = Date()
        var rows: [String] = []
        var metaKeys = Set<String>()
        var lastUsage: LanguageModelSession.Usage?
        var lastText = ""
        do {
            let stream = session.streamResponse(to: prompt, options: opts)
            for try await snap in stream {
                let t = Date().timeIntervalSince(t0)
                let u = snap.usage
                for k in u.metadata.keys { metaKeys.insert(k) }
                rows.append(String(format: "%.4f\t%d\t%d\t%d", t, snap.content.count, u.output.totalTokenCount, u.input.totalTokenCount))
                lastUsage = u
                lastText = snap.content
            }
        } catch { print("error: \(error)") }
        print("#label \(label)")
        print("#text " + lastText.replacingOccurrences(of: "\n", with: " / "))
        print("#meta_keys \(metaKeys.sorted())")
        if let u = lastUsage {
            print("#final input_total=\(u.input.totalTokenCount) cached=\(u.input.cachedTokenCount) output_total=\(u.output.totalTokenCount) reasoning=\(u.output.reasoningTokenCount)")
            for (k, v) in u.metadata { print("#meta \(k) = \(v)") }
        }
        print("t_s\tchars\toutput_tokens\tinput_tokens")
        for r in rows { print(r) }
    }
}
