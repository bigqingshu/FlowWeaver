using System.Globalization;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool TryParseNonNegativeInt(
        string input,
        string label,
        out int value,
        out string errorMessage)
    {
        if (int.TryParse(
            input,
            NumberStyles.Integer,
            CultureInfo.InvariantCulture,
            out value) &&
            value >= 0)
        {
            errorMessage = string.Empty;
            return true;
        }

        errorMessage = F("definition.runtime_options_number_invalid", label);
        return false;
    }

    private bool TryParseNonNegativeDouble(
        string input,
        string label,
        out double value,
        out string errorMessage)
    {
        if (double.TryParse(
            input,
            NumberStyles.Float,
            CultureInfo.InvariantCulture,
            out value) &&
            value >= 0)
        {
            errorMessage = string.Empty;
            return true;
        }

        errorMessage = F("definition.runtime_options_number_invalid", label);
        return false;
    }
}
