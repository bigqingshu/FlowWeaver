using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class DataPreviewSelectionStateTests
{
    [TestMethod]
    public void Resolve_PrefersCapturedStateBeforeCapturedTable()
    {
        var state = new DataPreviewSelectionState();
        state.Capture("run:source", "table-target");

        var resolution = state.Resolve(
        [
            Candidate("run:source", "table-source"),
            Candidate("run:target", "table-target"),
        ]);

        Assert.AreEqual("run:source", resolution.StateKey);
        Assert.AreEqual("table-source", resolution.TableRefId);
    }

    [TestMethod]
    public void Resolve_FallsBackToStateContainingCapturedTable()
    {
        var state = new DataPreviewSelectionState();
        state.Capture("run:missing", "table-target");

        var resolution = state.Resolve(
        [
            Candidate("run:source", "table-source"),
            Candidate("run:target", "table-target"),
        ]);

        Assert.AreEqual("run:target", resolution.StateKey);
        Assert.AreEqual("table-target", resolution.TableRefId);
    }

    [TestMethod]
    public void Resolve_FallsBackToFirstStateAndTable()
    {
        var state = new DataPreviewSelectionState();
        state.Capture("run:missing", "table-missing");

        var resolution = state.Resolve(
        [
            Candidate("run:source", "table-source", "table-extra"),
            Candidate("run:target", "table-target"),
        ]);

        Assert.AreEqual("run:source", resolution.StateKey);
        Assert.AreEqual("table-source", resolution.TableRefId);
    }

    [TestMethod]
    public void Resolve_PreservesCapturedTableWithinSelectedState()
    {
        var state = new DataPreviewSelectionState();
        state.Capture("run:source", "table-extra");

        var resolution = state.Resolve(
        [
            Candidate("run:source", "table-source", "table-extra"),
        ]);

        Assert.AreEqual("table-extra", resolution.TableRefId);
    }

    [TestMethod]
    public void Resolve_ReturnsEmptyResolutionWithoutCandidates()
    {
        var state = new DataPreviewSelectionState();
        state.Capture("run:source", "table-source");

        var resolution = state.Resolve([]);

        Assert.IsNull(resolution.StateKey);
        Assert.IsNull(resolution.TableRefId);
    }

    [TestMethod]
    public void Resolve_SkipsUnreadableGroupWhenNoPreferenceExists()
    {
        var state = new DataPreviewSelectionState();

        var resolution = state.Resolve(
        [
            Candidate("run:memory-unreadable"),
            Candidate("run:runtime-readable", "table-readable"),
        ]);

        Assert.AreEqual("run:runtime-readable", resolution.StateKey);
        Assert.AreEqual("table-readable", resolution.TableRefId);
    }

    [TestMethod]
    public void Resolve_UsesOrdinalKeysAndTableIds()
    {
        var state = new DataPreviewSelectionState();
        state.Capture("Run:Source", "Table-Source");

        var resolution = state.Resolve(
        [
            Candidate("run:source", "table-source"),
            Candidate("run:target", "table-target"),
        ]);

        Assert.AreEqual("run:source", resolution.StateKey);
        Assert.AreEqual("table-source", resolution.TableRefId);
    }

    private static DataPreviewStateSelectionCandidate Candidate(
        string stateKey,
        params string[] tableRefIds)
    {
        return new DataPreviewStateSelectionCandidate(stateKey, tableRefIds);
    }
}
