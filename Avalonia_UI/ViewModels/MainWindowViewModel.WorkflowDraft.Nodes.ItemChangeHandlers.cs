using System.ComponentModel;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void OnWorkflowDefinitionDraftNodeItemPropertyChanged(
        object? sender,
        PropertyChangedEventArgs args)
    {
        if (args.PropertyName == nameof(WorkflowDefinitionNodeListItemViewModel.IsBatchSelected))
        {
            RefreshWorkflowDefinitionBatchSelectionState();
        }
    }
}
