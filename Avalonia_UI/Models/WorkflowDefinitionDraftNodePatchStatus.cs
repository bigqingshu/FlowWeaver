namespace Avalonia_UI.Models;

public enum WorkflowDefinitionDraftNodePatchStatus
{
    Succeeded,
    JsonInvalid,
    RootNotObject,
    NodesMissing,
    ConnectionsMissing,
    NodeInstanceIdRequired,
    NodeTypeRequired,
    NodeVersionRequired,
    NodeAlreadyExists,
    NodeNotFound,
    ConfigUnsupported,
}
