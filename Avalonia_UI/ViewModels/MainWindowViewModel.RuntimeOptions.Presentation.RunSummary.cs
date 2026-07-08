using System;
using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private string FormatSelectedRunRuntimeOptionsSummary()
    {
        if (SelectedRun is null)
        {
            return T("definition.runtime_options_run_summary_empty");
        }

        var definitionJson = FindSelectedRunDefinitionJson();
        if (definitionJson is null)
        {
            return T("definition.runtime_options_run_summary_unavailable");
        }

        var readResult = RuntimeOptionsDraftReader.Read(definitionJson);
        if (!readResult.Succeeded)
        {
            return LocalizeWorkflowDefinitionDraftWarning(readResult.Warning)
                ?? readResult.Warning
                ?? T("definition.runtime_options_run_summary_unavailable");
        }

        return F(
            "definition.runtime_options_run_summary",
            FormatRuntimeOptionsOptionValue("profile", readResult.Draft.Workflow.Profile),
            FormatRuntimeOptionsOptionValue(
                "event_level",
                readResult.Draft.Workflow.Telemetry.EventLevel),
            readResult.Draft.Workflow.Telemetry.ProgressEnabled
                ? T("common.on")
                : T("common.off"),
            readResult.Draft.NodeOverrides.Count);
    }

    private string? FindSelectedRunDefinitionJson()
    {
        if (SelectedRun is null ||
            WorkflowDefinitionDetail is null ||
            !string.Equals(
                SelectedRun.WorkflowId,
                WorkflowDefinitionDetail.WorkflowId,
                StringComparison.Ordinal))
        {
            return null;
        }

        if (string.Equals(
            SelectedRun.RevisionId,
            WorkflowDefinitionDetail.RevisionId,
            StringComparison.Ordinal) ||
            (string.IsNullOrWhiteSpace(SelectedRun.RevisionId) &&
                SelectedRun.WorkflowVersion == WorkflowDefinitionDetail.Version))
        {
            return WorkflowDefinitionDetail.RawDefinitionJson;
        }

        return WorkflowDefinitionDetail.Revisions.FirstOrDefault(revision =>
            string.Equals(
                revision.RevisionId,
                SelectedRun.RevisionId,
                StringComparison.Ordinal))?.RawDefinitionJson;
    }
}
