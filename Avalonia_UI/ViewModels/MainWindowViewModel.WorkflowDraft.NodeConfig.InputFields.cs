using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void RebuildSelectedNodeConfigEditableInputFields(
        NodeConfigEditableDraft? editableDraft)
    {
        foreach (var field in SelectedNodeConfigEditableInputFields)
        {
            field.PropertyChanged -= OnSelectedNodeConfigFieldPropertyChanged;
        }

        CancelPendingNodeConfigAutoSave();
        hasUnappliedNodeConfigChanges = false;
        hasUnappliedSpecializedNodeConfigChanges = false;
        SelectedNodeConfigEditableInputFields.Clear();
        if (editableDraft is not null)
        {
            var nodeType = SelectedWorkflowDefinitionNode?.NodeType ?? string.Empty;
            foreach (var field in editableDraft.Fields)
            {
                var input = new NodeConfigEditableFieldInputViewModel(
                    field,
                    nodeType,
                    DisplayTextFormatter);
                input.PropertyChanged += OnSelectedNodeConfigFieldPropertyChanged;
                SelectedNodeConfigEditableInputFields.Add(input);
            }
        }

        OnPropertyChanged(nameof(HasSelectedNodeConfigEditableInputFields));
        OnPropertyChanged(nameof(ShowsGenericSelectedNodeConfigEditor));
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
    }
}
