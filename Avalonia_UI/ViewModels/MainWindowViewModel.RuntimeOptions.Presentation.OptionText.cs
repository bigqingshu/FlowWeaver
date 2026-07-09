namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private string FormatRuntimeOptionsOptionValue(string group, string value)
    {
        return DisplayTextFormatter.FormatRuntimeOptionsOptionValue(group, value);
    }
}
