namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private string BuildLimitRangeError(string label)
    {
        return F("format.limit_between", label);
    }

    private bool TryParseLimit(
        string limitFilter,
        string label,
        out int limit,
        out string? error)
    {
        limit = 100;
        error = null;

        var limitText = NormalizeFilter(limitFilter);
        if (limitText is null)
        {
            return true;
        }

        if (!int.TryParse(limitText, out var parsedLimit)
            || parsedLimit is < 1 or > 1000)
        {
            error = BuildLimitRangeError(label);
            return false;
        }

        limit = parsedLimit;
        return true;
    }

    private static string? NormalizeFilter(string value)
    {
        return string.IsNullOrWhiteSpace(value) ? null : value.Trim();
    }
}
