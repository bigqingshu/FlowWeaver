namespace Avalonia_UI.Models;

public enum WorkflowDefinitionDraftConnectionPatchStatus
{
    Succeeded,
    JsonInvalid,
    RootNotObject,
    NodesMissing,
    ConnectionsMissing,
    ConnectionIdRequired,
    SourceNodeIdRequired,
    SourcePortRequired,
    TargetNodeIdRequired,
    TargetPortRequired,
    ConnectionAlreadyExists,
    ConnectionNotFound,
    SourceNodeNotFound,
    TargetNodeNotFound,
}
