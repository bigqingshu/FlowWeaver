using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private NodeDefinitionListItemViewModel? selectedNewDraftNodeDefinition;

    [ObservableProperty]
    private string newDraftNodeInstanceId = string.Empty;

    [ObservableProperty]
    private string newDraftNodeType = string.Empty;

    [ObservableProperty]
    private string newDraftNodeVersion = "1.0";

    [ObservableProperty]
    private string newDraftNodeDisplayName = string.Empty;

    [ObservableProperty]
    private string newDraftNodeConfigJson = "{}";

    private string lastSuggestedNewDraftNodeInstanceId = string.Empty;
    private string lastSuggestedNewDraftNodeConfigJson = "{}";
}
