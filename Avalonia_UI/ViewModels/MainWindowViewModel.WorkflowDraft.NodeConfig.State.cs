using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void RefreshSelectedNodeDisplayNameDraftState()
    {
        SelectedNodeDisplayNameDraft = SelectedWorkflowDefinitionNode?.DisplayName ?? string.Empty;
    }

    private void RefreshSelectedNodeConfigDraftState()
    {
        if (WorkflowDefinitionDetail is null ||
            SelectedWorkflowDefinitionNode is null)
        {
            SelectedNodeConfigDraft = null;
            SelectedNodeConfigEditableDraft = null;
            RebuildSelectedNodeConfigEditableInputFields(null);
            SelectedNodeConfigEditableDraftMessage =
                DisplayTextFormatter.FormatSelectedNodeConfigDraftMissingSelection();
            OnPropertyChanged(nameof(SelectedNodeConfigDraftSummaryText));
            return;
        }

        var schema = FindNodeDefinition(SelectedWorkflowDefinitionNode)
            ?.ConfigSchemaDescriptor;
        var draft = NodeConfigDraftBuilder.Build(
            WorkflowDefinitionDraftJson,
            SelectedWorkflowDefinitionNode.NodeInstanceId,
            schema);

        SelectedNodeConfigDraft = draft;
        if (!draft.IsSupported)
        {
            SelectedNodeConfigEditableDraft = null;
            RebuildSelectedNodeConfigEditableInputFields(null);
            SelectedNodeConfigEditableDraftMessage =
                DisplayTextFormatter.FormatSelectedNodeConfigDraftSchemaUnavailable();
            OnPropertyChanged(nameof(SelectedNodeConfigDraftSummaryText));
            return;
        }

        var editableDraft = NodeConfigEditableDraftBuilder.Build(draft);
        SelectedNodeConfigEditableDraft = editableDraft;
        RebuildSelectedNodeConfigEditableInputFields(editableDraft);
        SelectedNodeConfigEditableDraftMessage =
            DisplayTextFormatter.FormatSelectedNodeConfigDraftReady(
                SelectedWorkflowDefinitionNode.NodeInstanceId,
                draft.Fields.Count(item => item.IsEditable),
                draft.Fields.Count(item => !item.IsEditable));
        OnPropertyChanged(nameof(SelectedNodeConfigDraftSummaryText));
    }

}
