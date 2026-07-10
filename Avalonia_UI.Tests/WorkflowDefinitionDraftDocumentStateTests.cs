using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowDefinitionDraftDocumentStateTests
{
    [TestMethod]
    public void IsDirty_InitialEmptyDraftIsClean()
    {
        var state = new WorkflowDefinitionDraftDocumentState();

        Assert.IsFalse(state.IsDirty(string.Empty));
    }

    [TestMethod]
    public void IsDirty_AcceptedDefinitionIsClean()
    {
        var state = new WorkflowDefinitionDraftDocumentState();
        state.AcceptOriginalDefinition("{\"nodes\":[]}");

        Assert.IsFalse(state.IsDirty("{\"nodes\":[]}"));
    }

    [TestMethod]
    public void IsDirty_ChangedDefinitionIsDirty()
    {
        var state = new WorkflowDefinitionDraftDocumentState();
        state.AcceptOriginalDefinition("{\"nodes\":[]}");

        Assert.IsTrue(state.IsDirty("{\"nodes\":[{}]}"));
    }

    [TestMethod]
    public void IsDirty_UsesOrdinalDefinitionComparison()
    {
        var state = new WorkflowDefinitionDraftDocumentState();
        state.AcceptOriginalDefinition("{\"Name\":\"A\"}");

        Assert.IsTrue(state.IsDirty("{\"name\":\"A\"}"));
    }
}
