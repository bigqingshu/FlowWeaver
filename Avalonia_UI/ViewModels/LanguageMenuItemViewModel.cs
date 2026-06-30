using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class LanguageMenuItemViewModel : ViewModelBase
{
    public LanguageMenuItemViewModel(SupportedLanguage language)
    {
        Code = language.Code;
        DisplayName = language.DisplayName;
    }

    public string Code { get; }

    public string DisplayName { get; }

    [ObservableProperty]
    private bool isSelected;
}
