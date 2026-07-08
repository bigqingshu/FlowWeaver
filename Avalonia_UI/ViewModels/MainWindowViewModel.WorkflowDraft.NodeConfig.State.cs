using System;
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

    private void RebuildSelectedNodeConfigEditableInputFields(
        NodeConfigEditableDraft? editableDraft)
    {
        SelectedNodeConfigEditableInputFields.Clear();
        if (editableDraft is not null)
        {
            var nodeType = SelectedWorkflowDefinitionNode?.NodeType ?? string.Empty;
            foreach (var field in editableDraft.Fields)
            {
                SelectedNodeConfigEditableInputFields.Add(
                    new NodeConfigEditableFieldInputViewModel(
                        field,
                        nodeType,
                        DisplayTextFormatter));
            }
        }

        OnPropertyChanged(nameof(HasSelectedNodeConfigEditableInputFields));
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
    }

    private static string? FormatNodeConfigApplyErrors(
        NodeConfigEditableDraftConfigResult result)
    {
        var fieldWarningCodes = result.FieldErrors
            .Select(error => error.Warning)
            .ToHashSet(StringComparer.Ordinal);
        var issueLines = result.FieldErrors
            .Select(error => $"{error.FieldName}: {error.Warning}")
            .Concat(result.Warnings.Where(warning => !fieldWarningCodes.Contains(warning)))
            .Where(line => !string.IsNullOrWhiteSpace(line))
            .ToArray();

        return issueLines.Length == 0
            ? null
            : string.Join(Environment.NewLine, issueLines);
    }
}
