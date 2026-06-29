using System;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public sealed class WorkflowListItemViewModel
{
    public WorkflowListItemViewModel(WorkflowDefinitionDto workflow)
    {
        WorkflowId = workflow.WorkflowId;
        Name = workflow.Name;
        RevisionId = workflow.RevisionId;
        Version = workflow.Version;
        Status = workflow.Status;
        UpdatedAt = workflow.UpdatedAt;
    }

    public string WorkflowId { get; }

    public string Name { get; }

    public string RevisionId { get; }

    public int Version { get; }

    public string Status { get; }

    public DateTimeOffset UpdatedAt { get; }

    public string VersionText => $"v{Version}";

    public string UpdatedAtText => UpdatedAt.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss");
}
