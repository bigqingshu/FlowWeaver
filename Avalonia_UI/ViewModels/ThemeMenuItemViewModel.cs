using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class ThemeMenuItemViewModel : ViewModelBase
{
    [ObservableProperty]
    private string name;

    [ObservableProperty]
    private string themeVariant;

    [ObservableProperty]
    private bool isSelected;

    public ThemeMenuItemViewModel(string name, string themeVariant)
    {
        Name = name;
        ThemeVariant = themeVariant;
    }
}
