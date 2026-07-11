using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplySelectedNodeConfigDraftMissingSelectionState()
    {
        ReplaceSelectedNodeSpecializedEditor(null);
        SelectedNodeConfigDraft = null;
        SelectedNodeConfigEditableDraft = null;
        RebuildSelectedNodeConfigEditableInputFields(null);
        SelectedNodeConfigEditableDraftMessage =
            DisplayTextFormatter.FormatSelectedNodeConfigDraftMissingSelection();
        OnPropertyChanged(nameof(SelectedNodeConfigDraftSummaryText));
    }

    private void ApplySelectedNodeConfigDraftSchemaUnavailableState()
    {
        ReplaceSelectedNodeSpecializedEditor(null);
        SelectedNodeConfigEditableDraft = null;
        RebuildSelectedNodeConfigEditableInputFields(null);
        SelectedNodeConfigEditableDraftMessage =
            DisplayTextFormatter.FormatSelectedNodeConfigDraftSchemaUnavailable();
        OnPropertyChanged(nameof(SelectedNodeConfigDraftSummaryText));
    }

    private void ApplySelectedNodeConfigDraftReadyState(
        NodeConfigDraft draft,
        NodeConfigEditableDraft editableDraft)
    {
        SelectedNodeConfigEditableDraft = editableDraft;
        RebuildSelectedNodeConfigEditableInputFields(editableDraft);
        RebuildSelectedNodeSpecializedEditor();
        SelectedNodeConfigEditableDraftMessage =
            DisplayTextFormatter.FormatSelectedNodeConfigDraftReady(
                SelectedWorkflowDefinitionNode!.NodeInstanceId,
                draft.Fields.Count(item => item.IsEditable),
                draft.Fields.Count(item => !item.IsEditable));
        OnPropertyChanged(nameof(SelectedNodeConfigDraftSummaryText));
    }
}
