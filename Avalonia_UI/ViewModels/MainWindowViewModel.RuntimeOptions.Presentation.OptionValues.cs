namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private static readonly string[] RuntimeOptionsProfileValues =
        ["normal", "background_fast", "diagnostic", "custom"];
    private static readonly string[] RuntimeOptionsLogLevelValues =
        ["DEBUG", "INFO", "WARN", "ERROR"];
    private static readonly string[] RuntimeOptionsEventLevelValues =
        ["none", "basic", "progress", "verbose"];
    private static readonly string[] RuntimeOptionsMaskPolicyValues =
        ["none", "partial", "full"];
}
