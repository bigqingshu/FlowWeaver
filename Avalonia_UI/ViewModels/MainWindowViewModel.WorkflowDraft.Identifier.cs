using System.Text;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private static string BuildSnakeCaseIdentifier(string source, string fallback)
    {
        var builder = new StringBuilder();
        for (var index = 0; index < source.Length; index++)
        {
            var current = source[index];
            if (char.IsLetterOrDigit(current))
            {
                var previous = index > 0 ? source[index - 1] : '\0';
                var next = index + 1 < source.Length ? source[index + 1] : '\0';
                var shouldSeparate =
                    char.IsUpper(current)
                    && builder.Length > 0
                    && builder[^1] != '_'
                    && (char.IsLower(previous)
                        || char.IsDigit(previous)
                        || char.IsLower(next));

                if (shouldSeparate)
                {
                    builder.Append('_');
                }

                builder.Append(char.ToLowerInvariant(current));
            }
            else if (builder.Length > 0 && builder[^1] != '_')
            {
                builder.Append('_');
            }
        }

        return builder.ToString().Trim('_') is { Length: > 0 } value
            ? value
            : fallback;
    }
}
