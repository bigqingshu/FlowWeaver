namespace Avalonia_UI.Models;

public enum WorkflowDefinitionDraftStructureStatus
{
    Supported,
    JsonInvalid,
    RootNotObject,
    NodesMissing,
    ConnectionsMissing,
}
