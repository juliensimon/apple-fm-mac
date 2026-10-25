import FoundationModels
import Foundation

@main struct I {
    static func main() async {
        let args = Array(CommandLine.arguments.dropFirst())
        var opts = GenerationOptions(); opts.samplingMode = .greedy; opts.maximumResponseTokens = 4
        for path in args {
            let session = LanguageModelSession()
            var usage: LanguageModelSession.Usage?
            do {
                let stream: LanguageModelSession.ResponseStream<String>
                if path == "none" {
                    stream = session.streamResponse(options: opts) { "Reply with the single word OK." }
                } else {
                    let url = URL(fileURLWithPath: path)
                    stream = session.streamResponse(options: opts) { "Reply with the single word OK."; Attachment(imageURL: url) }
                }
                for try await snap in stream { usage = snap.usage }
                print("\(path)\t\(usage?.input.totalTokenCount ?? -1)")
            } catch { print("\(path)\terror \(error)") }
        }
    }
}
