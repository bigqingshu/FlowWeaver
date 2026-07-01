using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public sealed class ShellNavigationItemViewModel : ViewModelBase
{
    private string headerText;

    public ShellNavigationItemViewModel(
        ShellPageDescriptor descriptor,
        string headerText)
    {
        Descriptor = descriptor;
        this.headerText = headerText;
    }

    public ShellPageDescriptor Descriptor { get; }

    public ShellPageKey Key => Descriptor.Key;

    public int SortOrder => Descriptor.SortOrder;

    public string HeaderPropertyName => Descriptor.HeaderPropertyName;

    public string ViewTypeName => Descriptor.ViewTypeName;

    public bool IsVisible => Descriptor.IsVisible;

    public bool IsEnabled => Descriptor.IsEnabled;

    public string HeaderText
    {
        get => headerText;
        private set => SetProperty(ref headerText, value);
    }

    public void RefreshHeaderText(string value)
    {
        HeaderText = value;
    }
}
