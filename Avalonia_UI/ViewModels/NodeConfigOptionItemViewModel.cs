namespace Avalonia_UI.ViewModels;

public sealed class NodeConfigOptionItemViewModel
{
    public NodeConfigOptionItemViewModel(string value, string displayText)
    {
        Value = value;
        DisplayText = displayText;
    }

    public string Value { get; }

    public string DisplayText { get; }
}
