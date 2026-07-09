using System.Collections.ObjectModel;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private string selectedNodeDisplayNameDraft = string.Empty;

    [ObservableProperty]
    private NodeConfigDraft? selectedNodeConfigDraft;

    [ObservableProperty]
    private NodeConfigEditableDraft? selectedNodeConfigEditableDraft;

    [ObservableProperty]
    private string selectedNodeConfigEditableDraftMessage = string.Empty;

    public ObservableCollection<NodeConfigEditableFieldInputViewModel>
        SelectedNodeConfigEditableInputFields { get; } = new();

    public bool HasSelectedNodeConfigEditableInputFields =>
        SelectedNodeConfigEditableInputFields.Count > 0;

    public string SelectedNodeConfigDraftSummaryText =>
        SelectedNodeConfigEditableDraftMessage;
}
